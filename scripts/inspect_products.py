import pandas as pd
import os, sys
path = 'data/products.xlsx'
if not os.path.exists(path):
    print('MISSING:', path)
    sys.exit(2)
try:
    df = pd.read_excel(path)
except Exception as e:
    print('ERROR reading Excel:', e)
    sys.exit(1)
cols = list(df.columns)
print('Columns:', cols)
img_cols = ['ImagePath','ImageBase64','Image','image','Image Url','ImageURL']
found = [c for c in img_cols if c in df.columns]
if found:
    for c in found:
        non_empty = int(df[c].notna().sum())
        print(f'Column {c} exists, non-empty count: {non_empty}')
else:
    print('No known image columns found in sheet.')
# show rows with any of found columns non-empty
if found:
    mask = False
    for c in found:
        mask = mask | df[c].notna()
    if mask.any():
        out_cols = [c for c in ['Device','Description'] if c in df.columns] + found
        print('Sample rows with image data:')
        print(df.loc[mask, out_cols].head(20).to_dict('records'))
    else:
        print('Image columns exist but all cells empty.')
else:
    # also try heuristic: any column with "image" in its lower name
    heur = [c for c in cols if 'image' in str(c).lower()]
    if heur:
        print('Heuristic image-like columns found:', heur)
        for c in heur:
            print(c, 'non-empty:', int(df[c].notna().sum()))
    else:
        print('No image data detected.')
