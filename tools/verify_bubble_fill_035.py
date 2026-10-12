"""Compare old and corrected native triangle fans; dry first, model only."""
import argparse,json,math
from pathlib import Path
from PIL import Image,ImageDraw
from check_english_bubbles_v3_live import area,signed,fan_check

UI=Path('work/ui/dialogue/0.1.35')
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');a=ap.parse_args()
    native=json.loads((UI/'native_installed.en.json').read_text());records=[]
    panel=Image.new('RGB',(960,624),'#36495b');draw=ImageDraw.Draw(panel)
    for row_index,names in enumerate((('reported_p101041_0','reported_p101041_1'),('reported_p101041_4',))):
        for column in range(2):
            offset=(column*480,40+row_index*292)
            draw.text((offset[0]+8,offset[1]-22),'Old native fill'if column==0 else'Corrected native fill',fill='white')
            for name in names:
                r=next(r for r in native['cases']if r['case']==name);cx,cy=r['center']
                poly=[[math.trunc(x+cx),math.trunc(y+cy)]for x,y in r['outline']]
                old=[math.trunc(cx),math.trunc(cy)];new=[math.trunc(v)for v in r['fan_origin']]
                excess=(sum(abs(area(old,x,y))for x,y in zip(poly,poly[1:]+poly[:1]))-abs(signed(poly)))/2
                fan_check(poly,new,name)
                if column==0:
                    if excess<=0:raise ValueError('Reported old defect not reproduced')
                    records.append(dict(case=name,old_absolute_triangle_area_excess_px2=excess,new_triangle_area_excess_px2=0,
                                        corrected_fan_origin=new,original_fan_origin=old))
                hub=old if column==0 else new
                for x,y in zip(poly,poly[1:]+poly[:1]):
                    draw.polygon([(p[0]+offset[0],p[1]+offset[1])for p in (hub,x,y)],fill='white')
                draw.line([(p[0]+offset[0],p[1]+offset[1])for p in poly+[poly[0]]],fill='black',width=2)
    proof=dict(version='0.1.35',candidate_sha256=native['candidate_sha256'],iso_sha256=native['loaded_iso_sha256'],
               records=records,model='GE triangle fan positions with native integer truncation; border texture/text/portraits omitted',
               natural_scene_capture=False,injected_capture_result='Full native draw calls completed, but captures did not establish visible shapes. A later injected probe timed out; final startup QA uses a fresh unmodified emulator session.')
    print(json.dumps(proof,indent=2))
    if not a.write:return
    out=UI/'fill_regression.en.json'
    if out.exists():raise ValueError('Fresh evidence required')
    out.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8');panel.save(UI/'fill_regression_model.png')
if __name__=='__main__':main()
