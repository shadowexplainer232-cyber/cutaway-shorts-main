# Voices

Voices are **not stored in this repo**. On the first run, `src/tts.py` downloads the voice named in
`config/brand.yml` (`voice.name`) with `python -m piper.download_voices`, and the workflow caches it.

## Candidates to audition (English)
| Voice id | Character | Note |
|---|---|---|
| `en_US-ryan-high` | male, clear, neutral | default in the package |
| `en_US-lessac-medium` | male/neutral, very common | smaller and faster |
| `en_US-amy-medium` | female, warm | |
| `en_GB-alan-medium` | British male | |

I have not listened to these or confirmed that they exist under these exact ids. Check the list at
the Piper voices page before first use; if a name is rejected, the download step fails loudly.

## Before you monetise
Each Piper voice comes from a different dataset with its own licence and model card. The Piper
program and its voices are licensed separately. **Read the model card of the voice you pick and
confirm it allows commercial use** before the channel is monetised. Not verified yet.

## Tuning
`voice.length_scale` in `config/brand.yml`: above 1.0 is slower, below 1.0 is faster. Try 1.0-1.1
for a calm explainer pace. The script length target is 25-50 seconds; the build warns above 59.

## Music
`assets/music/` is empty on purpose. Add only tracks whose licence permits YouTube use, then set
`music.file` in `config/brand.yml`.
