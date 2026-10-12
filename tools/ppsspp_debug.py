"""Local PPSSPP debugger client. Uses only an isolated emulator session."""
import argparse, base64, json, pathlib, sys, time

PACKAGES = pathlib.Path(__file__).resolve().parents[1] / 'work/source/analysis_packages'
sys.path.insert(0, str(PACKAGES))
import websocket


class Debugger:
    def __init__(self, port=45373):
        self.ws = websocket.create_connection(
            f'ws://127.0.0.1:{port}/debugger', timeout=10,
            subprotocols=['debugger.ppsspp.org'], http_proxy_host=None)
        self.ticket = 0

    def call(self, event, timeout=10, expect=None, **args):
        self.ticket += 1
        ticket = str(self.ticket)
        self.ws.send(json.dumps(dict(event=event, ticket=ticket, **args)))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.ws.settimeout(max(.1, deadline-time.monotonic()))
            reply = json.loads(self.ws.recv())
            if reply.get('ticket') == ticket or (expect and reply.get('event') == expect):
                if reply.get('event') == 'error':
                    raise RuntimeError(reply)
                return reply
        raise TimeoutError(event)

    def read(self, address, size):
        return base64.b64decode(self.call('memory.read', address=address, size=size)['base64'])

    def screenshot(self, path):
        self.call('cpu.stepping', expect='cpu.stepping')
        try:
            reply = self.call('gpu.buffer.screenshot', type='uri', timeout=20)
            path = pathlib.Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(base64.b64decode(reply['uri'].split(',', 1)[1]))
            return {k:v for k,v in reply.items() if k != 'uri'}
        finally:
            self.call('cpu.resume', expect='cpu.resume')

    def tap(self, button, frames=4):
        return self.call('input.buttons.press', button=button, duration=frames)

    def close(self):
        self.ws.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port', type=int, default=45373)
    p.add_argument('--event', default='version')
    p.add_argument('--args', default='{}')
    p.add_argument('--screenshot', type=pathlib.Path)
    a = p.parse_args()
    d = Debugger(a.port)
    try:
        result = d.screenshot(a.screenshot) if a.screenshot else d.call(a.event, **json.loads(a.args))
        print(json.dumps(result, ensure_ascii=True, indent=2))
    finally:
        d.close()


if __name__ == '__main__':
    main()
