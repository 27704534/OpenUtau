using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using Xunit;

using OpenUtau.Core.Ustx;

namespace OpenUtau.Core.Format {
    public class SvpTest {
        readonly string basePath;
        readonly string wavPath;

        public SvpTest() {
            var dir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            basePath = Path.Join(dir, "Files");
            wavPath = Path.Join(basePath, "sine.wav");
        }

        [Fact]
        public void LoadInstrumentalTrackPeaksNotNull() {
            Assert.True(File.Exists(wavPath), $"Test wav not found: {wavPath}");

            var svp = new {
                version = 2,
                time = new {
                    tempo = new[] { new { position = 0, bpm = 120.0 } },
                    meter = new[] { new { index = 0, numerator = 4, denominator = 4 } }
                },
                tracks = new[] {
                    new {
                        name = "Instrumental",
                        mainRef = new {
                            isInstrumental = true,
                            blickAbsoluteBegin = 0L,
                            audio = new {
                                filename = wavPath,
                                duration = 1.0
                            }
                        }
                    }
                }
            };

            string svpJson = JsonSerializer.Serialize(svp);
            string tempSvp = Path.Combine(basePath, "test_instrumental.svp");
            File.WriteAllText(tempSvp, svpJson);

            try {
                var project = SVP.Load(tempSvp);

                Assert.NotNull(project);
                Assert.NotEmpty(project.parts);

                var waveParts = project.parts.OfType<UWavePart>().ToList();
                Assert.NotEmpty(waveParts);

                foreach (var wavePart in waveParts) {
                    Assert.NotNull(wavePart.Peaks);
                }
            } finally {
                if (File.Exists(tempSvp)) {
                    File.Delete(tempSvp);
                }
            }
        }
    }
}