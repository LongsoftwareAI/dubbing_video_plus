import edge_tts, asyncio
voices = asyncio.run(edge_tts.list_voices())
print(f"Total EdgeTTS voices: {len(voices)}")
by_locale = {}
for v in voices:
    loc = v["Locale"]
    by_locale.setdefault(loc, []).append(v["ShortName"])
for loc in sorted(by_locale.keys()):
    names = by_locale[loc]
    print(f"  {loc:12s} ({len(names)} voices): {', '.join(names)}")
