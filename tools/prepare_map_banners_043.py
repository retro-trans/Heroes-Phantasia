"""Prepare the complete observed dungeon-banner category; dry-run by default."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
from PIL import Image, ImageDraw, ImageFont
from audit_dungeon_banners import audit
from inspect_font_assets import texture, unswizzle
from title_stamp import swizzle
from unpack_cpk import inventory, crilayla
from prepare_dungeon_banner import prepare as forest
from prepare_hold_banner import prepare as headquarters

VERSION = '0.1.43'
BASE = Path('work/output/0.1.42-title-credit-vwf-4x-candidate/HP.CPK')
FONT = Path('work/source/ppsspp/assets/Roboto_Condensed-Italic.ttf')
LABELS = Path('work/ui/map_banners/labels.en.json')
OUT = Path('work/output/0.1.43-map-banner-assets')
UI = Path('work/ui/map_banners/0.1.43')

def digest(b):
    return hashlib.sha256(b).hexdigest()

def extracted(path, row):
    with path.open('rb') as f:
        f.seek(row['offset']); data = f.read(row['stored_size'])
    return crilayla(data, row['extract_size']) if row['compression'] == 'CRILAYLA' else data

def prepare():
    labels = json.loads(LABELS.read_text(encoding='utf-8'))
    observations, _ = audit()
    known = {r['resource']: r for r in observations if 'dimensions' in r}
    rows = labels['rows']
    if len(rows) != 30 or {'fld/dngn/'+r['asset']+'.bin' for r in rows} != set(known):
        raise ValueError('Transcription must cover every observed banner exactly once')
    _, base_rows = inventory(BASE); base_by_name = {r['path']:r for r in base_rows}
    glossary = json.loads(Path('work/glossary/glossary.en.json').read_text(encoding='utf-8'))['entries']
    extra = json.loads(Path('work/glossary/world_map_ui_terms.en.json').read_text(encoding='utf-8'))['terms']
    glossary += extra
    reports, assets, pictures, missing = [], {}, [], []
    for row in rows:
        name = 'fld/dngn/'+row['asset']+'.bin'; observation = known[name]
        hits = [e for e in glossary if e['ja'] == row['source']]
        if hits and row['target'] not in {e['en'] for e in hits}:
            raise ValueError('Target conflicts with existing glossary: '+name)
        if not hits or all(e['id'].startswith('map_banner_') for e in hits):
            missing.append(dict(id='map_banner_'+row['asset'], category='location', ja=row['source'], en=row['target'],
                sources=['local:'+name, *labels['sources']], confidence='project_translation_original_bitmap_and_game_wiki',
                notes='Complete bitmap label. Compound organization/franchise spelling follows the existing glossary; no official English game localization verified.'))
        original_data = (Path('work/source/cpk')/name).read_bytes()
        if digest(original_data) != observation['source_sha256']:
            raise ValueError('Observed source changed: '+name)
        before = extracted(BASE, base_by_name[name])
        offsets = struct.unpack_from('<4I', original_data)
        t = texture(original_data, offsets[2], offsets[3])
        pal = [tuple(t['palette'][i:i+4]) for i in range(0,1024,4)]
        original = Image.frombytes('RGBA',(256,32), b''.join(bytes(pal[i]) for i in unswizzle(t['pixels'],256,32)))
        if row['asset'] in ('d01','d06'):
            candidate, previous, _, proposed = (headquarters if row['asset']=='d01' else forest)()
            if before != candidate:
                raise ValueError('Previously translated banner differs: '+name)
            size = previous['font_native_pixels']; changed = False
        else:
            if before != original_data:
                raise ValueError('Unexpected prior changes to banner: '+name)
            for size in range(26,11,-1):
                font = ImageFont.truetype(str(FONT),size*4); box=font.getbbox(row['target'])
                if math.ceil((box[2]-box[0])/4)<=251 and math.ceil((box[3]-box[1])/4)<=27:
                    break
            else:
                raise ValueError('Complete name cannot fit: '+row['target'])
            mask4=Image.new('L',(1024,128))
            ImageDraw.Draw(mask4).text((8-box[0],8-box[1]),row['target'],font=font,fill=255)
            mask=mask4.resize((256,32),Image.Resampling.LANCZOS)
            nearest=[min(range(256),key=lambda i:sum((a-b)**2 for a,b in zip((255,255,255,alpha),pal[i]))) for alpha in range(256)]
            linear=bytes(nearest[a] for a in mask.tobytes()); packed=swizzle(linear,256,32)
            if unswizzle(packed,256,32)!=linear:
                raise ValueError('Swizzle roundtrip differs')
            candidate=original_data[:t['pixel_offset']]+packed+original_data[t['pixel_offset']+len(packed):]
            proposed=Image.frombytes('RGBA',(256,32), b''.join(bytes(pal[i]) for i in linear)); changed=True
        p=t['pixel_offset']; end=p+8192
        if len(candidate)!=len(before) or candidate[:p]!=before[:p] or candidate[end:]!=before[end:]:
            raise ValueError('Nonpixel bytes changed: '+name)
        if proposed.getbbox() is None or proposed.getbbox()[2]>256 or proposed.getbbox()[3]>32:
            raise ValueError('Ink outside texture')
        reports.append(dict(resource=name,target=row['target'],source_sha256=digest(original_data),base_sha256=digest(before),
            candidate_sha256=digest(candidate),bytes=len(candidate),texture_offset=t['offset'],pixel_offset=p,pixel_bytes=8192,
            palette_sha256=digest(t['palette']),dimensions=[256,32],font_native_pixels=size,raster_scale=4,
            candidate_ink_bounds=list(proposed.getbbox()),changed=changed,all_nonpixel_bytes_preserved=True,swizzle_roundtrip=True))
        if changed:assets[name]=candidate
        pictures.append((row['asset'],row['target'],proposed))
    report=dict(schema_version=1,version=VERSION,base_archive=str(BASE),labels_sha256=digest(LABELS.read_bytes()),font=str(FONT),
        font_sha256=digest(FONT.read_bytes()),banner_count=30,new_translations=len(assets),retained_English_banners=2,
        excluded_non_banner_containers=[r['resource'] for r in observations if 'dimensions' not in r],
        entries=reports,missing_glossary_entries=missing,native_display_verified=False,
        scope='All observed 256x32 dungeon-entry name images; five different containers have no corresponding banner section. Textures supersampled at 4x, native allocation and consumer unchanged.')
    return report,assets,pictures

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--write-review',action='store_true');p.add_argument('--write-assets',action='store_true')
    p.add_argument('--write-data',action='store_true');p.add_argument('--expected-report-sha256');a=p.parse_args()
    report,assets,pictures=prepare(); encoded=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    key=digest(encoded.encode('utf-8'))
    print(json.dumps(dict(report_sha256=key,banner_count=30,new_translations=len(assets),retained=2,
        sample=[{'resource':r['resource'],'target':r['target'],'font_pixels':r['font_native_pixels']} for r in report['entries']],
        new_glossary_terms=[{'id':r['id'],'en':r['en']} for r in report['missing_glossary_entries']]),indent=2))
    if not any((a.write_review,a.write_assets,a.write_data)):
        print('DRY RUN: no data, image or asset files written.');return
    if sum((a.write_review,a.write_assets,a.write_data))!=1 or a.expected_report_sha256!=key:
        raise ValueError('One write action and exact reviewed report hash required')
    if a.write_review:
        if UI.exists():raise ValueError('Fresh review directory required')
        UI.mkdir(parents=True)
        sheet=Image.new('RGB',(576,56*15),'#ececec');d=ImageDraw.Draw(sheet)
        for n,(asset,target,im) in enumerate(pictures):
            im.save(UI/(asset+'.png'));x=(n%2)*288+4;y=(n//2)*56
            d.text((x,y+2),asset,fill='black')
            sheet.paste(Image.new('RGB',im.size,'black'),(x,y+18),im.getchannel('A'))
        sheet.save(UI/'english_assets.png');(UI/'proposal.en.json').write_text(encoded,encoding='utf-8')
    elif a.write_assets:
        if OUT.exists():raise ValueError('Fresh assets required')
        OUT.mkdir(parents=True)
        for name,data in assets.items():
            dest=OUT/Path(name).name;dest.write_bytes(data)
            if dest.read_bytes()!=data:raise ValueError('Asset readback differs')
        (OUT/'proposal.en.json').write_text(encoded,encoding='utf-8')
    else:
        g=Path('work/glossary/map_banner_terms.en.json')
        if g.exists():raise ValueError('Fresh glossary source required')
        g.write_text(json.dumps(dict(schema_version=1,version=VERSION,language='en',entries=report['missing_glossary_entries']),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        labels=json.loads(LABELS.read_text(encoding='utf-8'))['rows'];newrows=[]
        for row,r in zip(labels,report['entries']):
            newrows.append(dict(id='bitmap_dngn_'+row['asset']+'_name',file=r['resource'],offset=r['texture_offset'],
                encoding='baked_raster_source_transcription',category='dungeon_name_bitmap',source=row['source'],target=row['target'],
                status='prepared_static_reviewed_native_display_pending',context='Dungeon-entry location banner bitmap.',
                decisions='Existing glossary spelling or researched compound location name; full name fits original allocation at 4x raster scale. Preserve palette, UVs and all nonpixel bytes.',version=VERSION))
        Path('work/translation/en/bitmaps/dungeon_banner_0001.json').write_text(json.dumps(dict(schema_version=1,language='en',rows=newrows),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
