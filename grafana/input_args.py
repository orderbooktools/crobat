import recorder_full_w_prices as rec
import asyncio, time
from datetime import datetime
import copra.rest
from copra.websocket import Channel, Client

def main():
    settings = rec.input_args(recording_duration=2)
    loop = asyncio.get_event_loop()
    channel = Channel('level2', settings.currency_pair) 
    channel2 =Channel('ticker', settings.currency_pair)
    ws = rec.L2_Update(loop, channel, settings)
    ws.subscribe(channel2)
    count = 0
    timestart=datetime.utcnow()

    try:     
       loop.run_forever()

    except KeyboardInterrupt:
        loop.run_until_complete(ws.close())
        loop.close()

if __name__ == '__main__':
    main()