"""Native geometry model for reviewed .34 records; not an in-game screenshot."""
import argparse,json,struct
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from prepare_bubble_reflows_034 import build,BASE
from executable_text_patch import Elf
from dialogue_tokens import tokenize_bytes
from rebuild_dialogue import parse

OUT=Path('work/ui/dialogue/0.1.34/layout_model.png')
CASES=[('field_cougar','fld/talk/f101070.bin',0,'Cougar'),
       ('scene_p101041_17','phase/bin/p101041.bin',17,'Cougar'),
       ('scene_p101041_24','phase/bin/p101041.bin',24,'Shinobu'),
       ('scene_p101041_26','phase/bin/p101041.bin',26,'Mitch'),
       ('scene_p101041_27','phase/bin/p101041.bin',27,'Shinobu')]

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');a=ap.parse_args()
    _,assets,_=build();p=json.loads(Path('work/ui/dialogue/0.1.34/native_installed_extended.en.json').read_text())
    print(json.dumps(dict(output=str(OUT),cases=[r[0] for r in CASES],scope=__doc__),indent=2))
    if not a.write:return
    if OUT.exists():raise ValueError('Fresh preview required')
    executable=(BASE/'EBOOT.BIN').read_bytes();e=Elf(executable)
    widths=struct.unpack('<131I',executable[e.file_offset(0x2e4000):][:524])
    font=ImageFont.truetype('C:/Program Files/PPSSPP/assets/Roboto_Condensed-Regular.ttf',64)
    label=ImageFont.truetype('C:/Program Files/PPSSPP/assets/Roboto_Condensed-Regular.ttf',28)
    sheet=Image.new('RGB',(1960,1800),'#18232f');d=ImageDraw.Draw(sheet)
    d.text((20,8),'Layout model from native instructions - not in-game captures',font=label,fill='white')
    for index,(name,resource,ref,speaker)in enumerate(CASES):
        panel=Image.new('RGB',(1920,1088),'#405367');q=ImageDraw.Draw(panel)
        row=next(r for r in p['cases'] if r['case']==name);cx,cy=row['center']
        for bank,color in ((row['fill_banks'][1],'black'),(row['fill_banks'][0],'white')):
            q.polygon([((x+cx)*4,(y+cy)*4) for x,y in bank],fill=color)
        parsed=parse(resource,assets[resource]);raw=parsed['spans'][parsed['refs'][ref][1]][0].split(b'\x0e',1)[1]
        lines=[[]];red=False
        for token in tokenize_bytes(raw,True):
            if token.kind=='latin':lines[-1].append((token.code,red))
            elif token.code==0x11:lines.append([])
            elif token.code in (0x10,0x0e):break
            elif token.code==0x16:red=token.argument==b'03'
        for line_index,line in enumerate(lines):
            advance=sum(widths[c] for c,_ in line);x=cx-advance/2;y=cy+row['body_text_offset'][1]+line_index*22
            for code,colored in line:
                q.text((x*4,(y+12)*4),chr(code),font=font,fill='red'if colored else'black',anchor='ls');x+=widths[code]
        q.text((20,1020),speaker+' | '+name,font=label,fill='white')
        panel=panel.resize((960,544),Image.Resampling.LANCZOS)
        sheet.paste(panel,(20+(index%2)*980,60+(index//2)*580))
    sheet.save(OUT)
if __name__=='__main__':main()
