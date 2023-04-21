import asyncio
import threading

# 定义一个专门创建事件循环loop的函数，在另一个线程中启动它
def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def new_thread_loop():
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=start_loop, args=(loop,))  # 通过当前线程开启新的线程去启动事件循环
    t.start()
    return loop


