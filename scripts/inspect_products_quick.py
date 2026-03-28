import pandas as pd, os, sys
p='data/products.xlsx'
if not os.path.exists(p):
    print('MISSING')
    sys.exit(0)
df=pd.read_excel(p)
cols=list(df.columns)
print('COLUMNS:', cols)
for c in ['ImagePath','ImageBase64','Image','image','Image Url','ImageURL']:
    if c in df.columns:
        print(c, 'non-empty count=', int(df[c].notna().sum()))
# heuristic: any column containing 'image'
heur=[c for c in cols if 'image' in str(c).lower()]
print('heuristic image-like:', heur)
