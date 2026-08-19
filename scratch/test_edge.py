import asyncio
import edge_tts
import os

async def test():
    c = edge_tts.Communicate("Xin chao, toi la mot con robot.", "vi-VN-HoaiMyNeural")
    out = "d:/tool/omivoice/test_mini_tool/cache/test_edge.mp3"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    await c.save(out)
    print(f"EdgeTTS OK, file size: {os.path.getsize(out)} bytes")

asyncio.run(test())
