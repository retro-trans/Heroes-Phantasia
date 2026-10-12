"""Prepare proportional English atlas prototypes. Does not patch game rendering.

Default dry-run reports metrics; --write creates native and 4x PNGs and JSON.
"""
import argparse, hashlib, json, math, pathlib
from PIL import Image, ImageDraw, ImageFont

GLYPHS=''.join(chr(x) for x in range(32,127))+'\u2018\u2019\u201c\u201d\u2013\u2014\u2026\u00d7\u00e8'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--font',type=pathlib.Path,default=pathlib.Path('C:/Program Files/PPSSPP/assets/Roboto_Condensed-Regular.ttf'))
    p.add_argument('--output',type=pathlib.Path,default=pathlib.Path('work/ui/vwf'))
    p.add_argument('--write',action='store_true');a=p.parse_args()
    font=ImageFont.truetype(str(a.font),16)
    metrics={c:{'advance_26_6':round(font.getlength(c)*64),'advance_px':round(font.getlength(c),4),
                'atlas_cell':[i%16*32,i//16*32,32,32],
                'bbox_baseline':list(font.getbbox(c,anchor='ls'))} for i,c in enumerate(GLYPHS)}
    if metrics['i']['advance_px']>=metrics['W']['advance_px']:raise ValueError('Font is not proportional')
    for char,m in metrics.items():
        x0,y0,x1,y1=m['bbox_baseline']
        if min(x0+4,y0+22)<0 or max(x1+4,y1+22)>32:raise ValueError('Glyph clips: '+char)
    info={'version':'0.1.0','status':'prototype_not_integrated_or_tested_in_game',
          'font_name':font.getname(),'font_source':str(a.font),'font_sha256':hashlib.sha256(a.font.read_bytes()).hexdigest(),
          'license':'Apache-2.0; see Roboto-LICENSE.txt',
          'native_font_size':16,'native_line_height':24,'native_baseline':22,
          'native_atlas_size':[512,256],'4x_atlas_size':[2048,1024],
          'glyph_count':len(GLYPHS),'metrics':metrics,
          'integration':'Needs decoder/glyph-map/layout hooks, wrapping, clipping and relocation; 4x atlas targets emulator feasibility investigation. Native fallback supplied.'}
    print(json.dumps({'glyphs':len(GLYPHS),'font':font.getname(),'width_i':metrics['i']['advance_px'],
        'width_W':metrics['W']['advance_px'],'native':[512,256],'4x':[2048,1024],
        'status':info['status']},indent=2))
    if not a.write:print('DRY RUN: no files written.');return
    a.output.mkdir(parents=True,exist_ok=True)
    for scale in (1,4):
        atlas=Image.new('RGBA',(512*scale,256*scale),(255,255,255,0));draw=ImageDraw.Draw(atlas)
        raster_font=ImageFont.truetype(str(a.font),16*scale)
        for i,c in enumerate(GLYPHS):draw.text(((i%16*32+4)*scale,(i//16*32+22)*scale),c,font=raster_font,anchor='ls',fill='white')
        atlas.save(a.output/f'english_vwf_{scale}x.png')
    (a.output/'english_vwf_metrics.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
    canvas=Image.new('RGB',(800,210),'#141d2a');d=ImageDraw.Draw(canvas)
    title=ImageFont.truetype(str(a.font),22);sample=ImageFont.truetype(str(a.font),24)
    d.text((20,15),'English VWF prototype - renderer integration pending',font=title,fill='#e4ecf7')
    d.text((20,65),'Variable widths:  Illiterate villains will never win!',font=sample,fill='#d9f4ff')
    d.text((20,110),'Narrow i / wide W:   iiiii WWWWW',font=sample,fill='#ffce80')
    d.text((20,162),'Native atlas + independently rasterized 4x atlas; original ISO unchanged.',font=font,fill='#c5cfdd')
    canvas.save(a.output/'vwf_preview.png')
    print('Created font prototypes in',a.output)

if __name__=='__main__':main()
