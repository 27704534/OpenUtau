using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using OpenUtau.Api;
using OpenUtau.Core.Ustx;
using Serilog;
using WanaKanaNet;

namespace OpenUtau.Plugin.Builtin {
    /// <summary>
    /// Cross-lingual phonemizer that converts Chinese pinyin lyrics to
    /// Japanese VCV (renzokuon / continuous-sound) aliases.
    ///
    /// Unlike the CV version ("ZH to JA") which outputs standalone romaji,
    /// this phonemizer links adjacent phonemes by prepending the previous
    /// vowel, forming the characteristic VCV transition:
    ///   phrase start → "- tsu" / "- a"
    ///   between notes → "u shi" / "a n"
    ///   within a note → "u a" / "a o"
    ///
    /// This is designed for VCV (continuous) Japanese voicebanks.
    /// </summary>
    [Phonemizer("Chinese to Japanese VCV Phonemizer", "ZH to JA VCV", language: "ZH")]
    public class ChineseToJapaneseVCVPhonemizer : Phonemizer {

        private USinger? singer;
        private Dictionary<string, WeightedScheme[]> mapping = null!;
        private bool? useKana; // null=undetected, true=hiragana, false=romaji

        private readonly record struct WeightedOption(int Ratio, string Romaji);
        private readonly record struct WeightedScheme(WeightedOption[] Options);

        private const double OverlapMs = 80;
        private const string VcvPad = " "; // separator between prev-vowel and current romaji

        // ── ctor ─────────────────────────────────────────────────────

        public ChineseToJapaneseVCVPhonemizer() {
            try {
                LoadMapping();
            } catch (Exception e) {
                Log.Error(e, "Failed to load pinyin mapping");
                mapping = new Dictionary<string, WeightedScheme[]>();
            }
        }

        // ── mapping loader (same source as ChineseToJapanesePhonemizer)

        private void LoadMapping() {
            mapping = new Dictionary<string, WeightedScheme[]>();
            var assembly = Assembly.GetExecutingAssembly();
            using var stream = assembly.GetManifestResourceStream(
                "OpenUtau.Plugin.Builtin.Data.pinyin_zh_to_ja.txt");
            if (stream == null) {
                Log.Error("Embedded resource pinyin_zh_to_ja.txt not found");
                return;
            }
            using var reader = new StreamReader(stream, Encoding.UTF8);

            string? line;
            while ((line = reader.ReadLine()) != null) {
                line = line.Trim();
                if (line.Length == 0 || line[0] == '#' || !line.Contains(';'))
                    continue;
                var parts = line.Split(';', 2);
                if (parts.Length != 2) continue;
                string pinyin = parts[0].Trim();
                if (pinyin.Length == 0) continue;

                var schemeStrs = parts[1].Trim().Split('_');
                var schemes = new List<WeightedScheme>();
                foreach (var schemeStr in schemeStrs) {
                    var tokens = schemeStr.Split(',');
                    var opts = new List<WeightedOption>();
                    bool valid = true;
                    foreach (var token in tokens) {
                        var dot = token.IndexOf('.');
                        if (dot <= 0) { valid = false; break; }
                        if (!int.TryParse(token.AsSpan(0, dot), out int ratio) || ratio <= 0)
                            { valid = false; break; }
                        string romaji = token.Substring(dot + 1).Trim();
                        if (romaji.Length == 0) { valid = false; break; }
                        opts.Add(new WeightedOption(ratio, romaji));
                    }
                    if (valid && opts.Count > 0)
                        schemes.Add(new WeightedScheme(opts.ToArray()));
                }
                if (schemes.Count > 0)
                    mapping[pinyin] = schemes.ToArray();
            }
        }

        // ── Phonemizer API ───────────────────────────────────────────

        public override void SetSinger(USinger singer) {
            this.singer = singer;
            useKana = null; // re-detect on next use
        }

        public override Result Process(Note[] notes, Note? prev, Note? next,
            Note? prevNeighbour, Note? nextNeighbour, Note[] prevs) {

            var note = notes[0];
            string lyric = note.lyric.Normalize();

            // Forced alias
            if (lyric.Length > 0 && lyric[0] == '?')
                return MakeSimpleResult(lyric.Substring(1));

            // Extension / rest / breath
            if (lyric == "+" || lyric.StartsWith("+~") || lyric.StartsWith("+*"))
                return MakeSimpleResult(lyric);
            if (lyric == "R" || lyric == "-")
                return MakeSimpleResult(lyric);

            // ── Look up the mapping (first scheme only) ──────────────
            WeightedOption[] scheme;
            if (!mapping.TryGetValue(lyric, out var schemes) || schemes.Length == 0) {
                // No mapping – pass through with VCV prefix
                var fallback = ConvertToVoicebankAlias(lyric, note.tone);
                string prevV = GetLastVowelOfNote(prevNeighbour);
                string alias = prevV != null
                    ? prevV + VcvPad + fallback
                    : "-" + VcvPad + fallback;
                return MakeSimpleResult(alias);
            }

            scheme = schemes[0].Options;
            int totalRatio = scheme.Sum(o => o.Ratio);
            int totalDuration = notes.Sum(n => n.duration);
            if (totalDuration <= 0) totalDuration = 480;

            // Overlap in ticks
            double bpm = timeAxis.GetBpmAtTick(note.position);
            double msPerTick = 60000.0 / (bpm * 480);
            int overlapTicks = (int)(OverlapMs / msPerTick);
            if (overlapTicks < 0) overlapTicks = 0;

            // ── Determine the linking vowel ──────────────────────────
            // For the FIRST sub-phoneme: use the previous note's last vowel,
            // or "-" if this is the start of a phrase.
            string? linkVowel = GetLastVowelOfNote(prevNeighbour);

            // ── Build phonemes ───────────────────────────────────────
            var phonemes = new List<Phoneme>();
            int cumulativePos = 0;

            for (int i = 0; i < scheme.Length; i++) {
                var opt = scheme[i];
                int phonemeDuration = totalDuration * opt.Ratio / totalRatio;
                if (phonemeDuration <= 0) phonemeDuration = 1;

                string baseRomaji = opt.Romaji;
                string alias = ConvertToVoicebankAlias(baseRomaji, note.tone);

                // Build VCV alias
                if (i == 0) {
                    // First sub-phoneme → linked from previous note or phrase start
                    alias = linkVowel != null
                        ? linkVowel + VcvPad + alias
                        : "-" + VcvPad + alias;
                } else {
                    // Subsequent sub-phonemes → linked from previous sub-phoneme
                    string prevVowel = ExtractVowel(scheme[i - 1].Romaji);
                    alias = prevVowel + VcvPad + alias;
                }

                int position = cumulativePos;
                if (i > 0) {
                    position -= overlapTicks;
                }

                phonemes.Add(new Phoneme {
                    phoneme = alias,
                    position = position,
                });

                cumulativePos += phonemeDuration;
            }

            return new Result { phonemes = phonemes.ToArray() };
        }

        // ── helpers ──────────────────────────────────────────────────

        /// <summary>
        /// Re-computes the last sub-phoneme vowel of the previous note
        /// by looking up its lyric in the mapping table.
        /// Returns null if there is no previous note or the lookup fails.
        /// </summary>
        private string? GetLastVowelOfNote(Note? prevNote) {
            if (prevNote == null) return null;

            string lyric = prevNote.Value.lyric.Normalize();
            if (string.IsNullOrEmpty(lyric) || lyric == "R" || lyric == "-")
                return null;
            if (lyric.Length > 0 && lyric[0] == '?')
                lyric = lyric.Substring(1);

            if (!mapping.TryGetValue(lyric, out var schemes) || schemes.Length == 0)
                return null;

            var opts = schemes[0].Options;
            if (opts.Length == 0) return null;

            return ExtractVowel(opts[^1].Romaji); // last sub-phoneme's vowel
        }

        /// <summary>
        /// Extracts the vowel from a Japanese romaji syllable.
        /// For CV syllables (ka, tsu, shi, kya) the vowel is the last character.
        /// "n" is treated as a syllabic nasal.
        /// </summary>
        private static string ExtractVowel(string romaji) {
            if (string.IsNullOrEmpty(romaji)) return "a";
            return romaji[^1].ToString();
        }

        /// <summary>
        /// Detects the voicebank format once by probing for "o あ" in the OTO.
        /// VCV kana banks use "<vowel> <kana>" format (e.g. "o あ", "a か").
        /// If "o あ" exists → hiragana mode; otherwise → romaji mode.
        /// </summary>
        private void DetectFormat() {
            useKana = false;
            if (singer == null || !singer.Found) return;
            if (singer.TryGetMappedOto("o あ", 60, out _))
                useKana = true;
        }

        /// <summary>
        /// Converts romaji to the voicebank's preferred format.
        /// Hiragana mode: WanaKana.ToHiragana().  Romaji mode: pass through.
        /// </summary>
        private string ConvertToVoicebankAlias(string romaji, int tone) {
            if (singer == null || !singer.Found)
                return romaji;
            if (useKana == null)
                DetectFormat();
            if (useKana == true) {
                try {
                    return WanaKana.ToHiragana(romaji);
                } catch { }
            }
            return romaji;
        }

        public override string ToString() => "[ZH to JA VCV] Chinese to Japanese VCV Phonemizer";
    }
}
