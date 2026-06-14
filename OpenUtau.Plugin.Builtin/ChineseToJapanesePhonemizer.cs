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
    /// Cross-lingual phonemizer that converts Chinese pinyin lyrics to Japanese romaji.
    /// Uses an embedded weighted mapping table (pinyin.txt) to split each Chinese syllable
    /// into one or more Japanese morae by weight ratio, then assigns overlap between
    /// non-first sub-phonemes for smoother transitions.
    ///
    /// For CV (standalone) voicebanks whose OTO aliases are in kana, romaji is
    /// automatically converted to hiragana.
    /// </summary>
    [Phonemizer("Chinese to Japanese Phonemizer", "ZH to JA", language: "ZH")]
    public class ChineseToJapanesePhonemizer : Phonemizer {

        private USinger? singer;
        private Dictionary<string, WeightedScheme[]> mapping = null!;

        /// <summary>(ratio, romaji) pair used in weighted mapping.</summary>
        private readonly record struct WeightedOption(int Ratio, string Romaji);

        /// <summary>One scheme = an array of weighted romaji options.</summary>
        private readonly record struct WeightedScheme(WeightedOption[] Options);

        private const double OverlapMs = 80;

        public ChineseToJapanesePhonemizer() {
            try {
                LoadMapping();
            } catch (Exception e) {
                Log.Error(e, "Failed to load pinyin mapping");
                mapping = new Dictionary<string, WeightedScheme[]>();
            }
        }

        // ── mapping loader ───────────────────────────────────────────

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

                // Each scheme separated by '_'
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
        }

        public override Result Process(Note[] notes, Note? prev, Note? next,
            Note? prevNeighbour, Note? nextNeighbour, Note[] prevs) {

            var note = notes[0];
            string lyric = note.lyric.Normalize();

            // Forced alias (? prefix)
            if (lyric.Length > 0 && lyric[0] == '?')
                return MakeSimpleResult(lyric.Substring(1));

            // Extension note
            if (lyric == "+" || lyric.StartsWith("+~") || lyric.StartsWith("+*"))
                return MakeSimpleResult(lyric);

            // Rest / breath / tail
            if (lyric == "R" || lyric == "-")
                return MakeSimpleResult(lyric);

            // Look up mapping → use first scheme (index 0)
            if (!mapping.TryGetValue(lyric, out var schemes) || schemes.Length == 0) {
                // No mapping – pass through (with kana conversion attempt)
                var fallback = ConvertToVoicebankAlias(lyric, note.tone);
                return MakeSimpleResult(fallback);
            }

            var scheme = schemes[0].Options;
            int totalRatio = scheme.Sum(o => o.Ratio);
            int totalDuration = notes.Sum(n => n.duration);
            if (totalDuration <= 0) totalDuration = 480;

            // Compute overlap in ticks: 80 ms expressed in ticks at current tempo
            double bpm = timeAxis.GetBpmAtTick(note.position);
            double msPerTick = 60000.0 / (bpm * 480);
            int overlapTicks = (int)(OverlapMs / msPerTick);
            if (overlapTicks < 0) overlapTicks = 0;

            var phonemes = new List<Phoneme>();
            int cumulativePos = 0;

            for (int i = 0; i < scheme.Length; i++) {
                var opt = scheme[i];
                int phonemeDuration = totalDuration * opt.Ratio / totalRatio;
                if (phonemeDuration <= 0) phonemeDuration = 1;

                string alias = ConvertToVoicebankAlias(opt.Romaji, note.tone);

                int position = cumulativePos;
                // Non-first phonemes overlap with the previous one for continuity
                if (i > 0) {
                    position -= overlapTicks;
                }

                phonemes.Add(new Phoneme {
                    phoneme = alias,
                    position = position,
                });

                cumulativePos += phonemeDuration;
            }

            // Fix: last phoneme should not extend beyond the total duration
            // (earlier phonemes' overlap shifts may have caused position misalignment)

            return new Result { phonemes = phonemes.ToArray() };
        }

        // ── helpers ──────────────────────────────────────────────────

        /// <summary>
        /// Tries the romaji alias against the singer's OTO.
        /// If not found, attempts hiragana conversion (for CV voicebanks
        /// whose aliases are in kana rather than romaji).
        /// Falls back to the original romaji string.
        /// </summary>
        private string ConvertToVoicebankAlias(string romaji, int tone) {
            if (singer == null || !singer.Found)
                return romaji;

            // 1) Try romaji directly
            if (singer.TryGetMappedOto(romaji, tone, out _))
                return romaji;

            // 2) Try hiragana conversion (for kana-aliased CV voicebanks)
            try {
                string hiragana = WanaKana.ToHiragana(romaji);
                if (hiragana != romaji && singer.TryGetMappedOto(hiragana, tone, out _))
                    return hiragana;
            } catch {
                // WanaKana may throw on non-romaji input
            }

            // 3) Fallback: return romaji as-is
            return romaji;
        }

        public override string ToString() => "[ZH to JA] Chinese to Japanese Phonemizer";
    }
}
