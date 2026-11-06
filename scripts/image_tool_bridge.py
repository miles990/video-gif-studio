"""Codex-compatible file queue for a host exposing the built-in image tool.

Use --codex scripts/image_tool_bridge.py with VGS_IMAGE_TOOL_QUEUE set to an
existing workspace directory. A host consumes request.json using its built-in
image tool and returns response.json {image_paths:[absolute PNG]}. This is an
explicit transport, never a fake image, paid fallback or provider API client.
The host must be present; unattended command-line use should use native Codex.
"""
import json,os,sys,time,uuid
from pathlib import Path

def main():
    queue=os.environ.get('VGS_IMAGE_TOOL_QUEUE')
    if not queue or not (Path(queue)/'host.json').exists():
        print('Built-in tool host unavailable');return 2
    if sys.argv[1:]==['login','status']:
        print('Logged in using ChatGPT built-in image tool host');return 0
    host=json.loads((Path(queue)/'host.json').read_text(encoding='utf8'))
    if len(list(Path(queue).glob('*/image.png')))>=host.get('max_images',20):
        print('Built-in tool host image budget exhausted; no request dispatched');return 2
    instruction=sys.stdin.read();marker='Use these tool parameters: '
    if marker not in instruction:raise ValueError('Missing image tool parameters')
    request=json.JSONDecoder().raw_decode(instruction.split(marker,1)[1])[0]
    folder=Path(queue)/uuid.uuid4().hex;folder.mkdir()
    temp=folder/'request.tmp';temp.write_text(json.dumps(request),encoding='utf8');temp.replace(folder/'request.json')
    deadline=time.monotonic()+1800
    while time.monotonic()<deadline:
        if (folder/'response.json').exists():
            result=json.loads((folder/'response.json').read_text(encoding='utf8'))
            if result.get('error'):print(json.dumps(result));return 2
            print(json.dumps(result));return 0
        time.sleep(.5)
    print('Image tool host timed out; reconcile queued request before retrying');return 2

if __name__=='__main__':raise SystemExit(main())
