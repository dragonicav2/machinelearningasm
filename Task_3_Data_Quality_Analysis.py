"""Task 3 data-quality analysis for the In-Vehicle Coupon Recommendation CSV.


The script writes CSV evidence tables and PNG charts to --output-dir. It reports
review indicators and does not automatically remove or alter source records.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import math
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

DEFAULT_OUT = Path(__file__).resolve().parent
TARGET = "Y"
DOMAINS = {
 "destination":{"No Urgent Place","Home","Work"},"passanger":{"Alone","Friend(s)","Kid(s)","Partner"},
 "weather":{"Sunny","Rainy","Snowy"},"temperature":{30,55,80},"time":{"7AM","10AM","2PM","6PM","10PM"},
 "coupon":{"Restaurant(<20)","Coffee House","Carry out & Take away","Bar","Restaurant(20-50)"},
 "expiration":{"1d","2h"},"gender":{"Female","Male"},"age":{"below21","21","26","31","36","41","46","50plus"},
 "maritalStatus":{"Unmarried partner","Single","Married partner","Divorced","Widowed"},"has_children":{0,1},
 "education":{"Some college - no degree","Bachelors degree","Associates degree","High School Graduate","Graduate degree (Masters or Doctorate)","Some High School"},
 "income":{"Less than $12500","$12500 - $24999","$25000 - $37499","$37500 - $49999","$50000 - $62499","$62500 - $74999","$75000 - $87499","$87500 - $99999","$100000 or More"},
 "Bar":{"never","less1","1~3","4~8","gt8"},"CoffeeHouse":{"never","less1","1~3","4~8","gt8"},
 "CarryAway":{"never","less1","1~3","4~8","gt8"},"RestaurantLessThan20":{"never","less1","1~3","4~8","gt8"},
 "Restaurant20To50":{"never","less1","1~3","4~8","gt8"},"toCoupon_GEQ5min":{1},
 "toCoupon_GEQ15min":{0,1},"toCoupon_GEQ25min":{0,1},"direction_same":{0,1},"direction_opp":{0,1},TARGET:{0,1}}
VISITS=["Bar","CoffeeHouse","CarryAway","RestaurantLessThan20","Restaurant20To50"]
TEMPERATURE_BANDS={30:"30-54",55:"55-79",80:"80+"}
TEMPERATURE_ORDER=["30-54","55-79","80+"]


def discover_csv(script_dir: Path) -> Path:
    """Find the dataset beside this script without accidentally choosing an unrelated file."""
    expected = script_dir / "in-vehicle-coupon-recommendation.csv"
    if expected.is_file():
        return expected
    candidates = sorted(script_dir.glob("*.csv"))
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise FileNotFoundError(
            f"No CSV file found beside the script in {script_dir}. "
            "Place the dataset there or pass --csv with its path."
        )
    choices = "\n".join(f"  - {item.name}" for item in candidates)
    raise ValueError(
        "More than one CSV file was found beside the script. "
        "Specify the intended dataset with --csv:\n" + choices
    )


def save_csv(frame,out,name):
    destination=out/name
    try:
        frame.to_csv(destination,index=False,encoding="utf-8-sig")
    except PermissionError as exc:
        raise PermissionError(
            f"Cannot write {destination}. Close this CSV if it is open in Excel, "
            "or rerun with --output-dir pointing to a new writable folder."
        ) from exc
def font(size):
    for f in [r"C:\Windows\Fonts\arial.ttf",r"C:\Windows\Fonts\segoeui.ttf"]:
        try:return ImageFont.truetype(f,size)
        except OSError:pass
    return ImageFont.load_default()
def width(draw,text,f): return draw.textbbox((0,0),str(text),font=f)[2]
def shorten(s,n):
    s=str(s)
    return s if len(s)<=n else s[:max(1,n-1)]+"…"
def bar_chart(path,title,labels,values,subtitle=None,width_px=1400,height_px=None,color=(36,122,132),sort=True):
    pairs=list(zip(map(str,labels),map(float,values)))
    if sort:pairs.sort(key=lambda x:x[1])
    if height_px is None:height_px=max(380,130+len(pairs)*34)
    im=Image.new("RGB",(width_px,height_px),"white");d=ImageDraw.Draw(im);ft=font(25);fl=font(16);fs=font(14)
    d.text((32,24),title,font=ft,fill=(18,48,74))
    if subtitle:d.text((34,62),subtitle,font=fs,fill=(85,98,108))
    left=min(max(max((width(d,shorten(x,32),fl) for x,_ in pairs),default=120)+45,220),width_px//2)
    right=width_px-115;top=105 if subtitle else 86;bottom=height_px-46
    plot_h=bottom-top;step=plot_h/max(1,len(pairs));mx=max([v for _,v in pairs]+[1]);
    for g in range(5):
        x=left+(right-left)*g/4;d.line((x,top,x,bottom),fill=(225,230,233),width=1);decimals=3 if mx<=1 else (1 if any(not float(v).is_integer() for _,v in pairs) else 0)
        d.text((x-23,bottom+8),f"{mx*g/4:,.{decimals}f}",font=fs,fill=(105,112,118))
    for i,(lab,val) in enumerate(pairs):
        y=top+i*step+step*.18;bh=max(4,step*.62);x2=left+(right-left)*val/mx
        d.text((left-12,y+bh/2),shorten(lab,32),font=fl,fill=(42,50,61),anchor="rm")
        d.rounded_rectangle((left,y,x2,y+bh),radius=4,fill=color)
        d.text((min(x2+7,right+8),y+bh/2),f"{val:,.{decimals}f}",font=fs,fill=(42,50,61),anchor="lm")
    im.save(path)
def panels(path,title,features,frame,ncols=3):
    w=1700;panel_h=390;rows=math.ceil(len(features)/ncols);h=105+rows*panel_h+20
    im=Image.new("RGB",(w,h),"white");d=ImageDraw.Draw(im);d.text((34,24),title,font=font(30),fill=(18,48,74))
    pw=(w-60)//ncols
    for ix,col in enumerate(features):
        row=ix//ncols;colpos=ix%ncols;x0=25+colpos*pw;y0=85+row*panel_h
        d.rounded_rectangle((x0,y0,x0+pw-12,y0+panel_h-15),radius=8,outline=(215,222,226),width=2)
        d.text((x0+15,y0+12),col,font=font(21),fill=(23,107,115))
        counts=frame[col].fillna("(Missing)").astype(str).value_counts().sort_values(ascending=True)
        max_items=10
        if len(counts)>max_items:
            other=counts.iloc[:-max_items].sum();counts=counts.iloc[-max_items:].copy();counts.loc["Other categories"]=other
        label_width=190;bar_left=x0+label_width;bar_right=x0+pw-75;bar_top=y0+55;bar_bottom=y0+panel_h-38
        step=(bar_bottom-bar_top)/max(1,len(counts));mx=max(counts.max(),1)
        for j,(lab,val) in enumerate(counts.items()):
            yy=bar_top+j*step+step*.2;bh=max(5,step*.58);xx=bar_left+(bar_right-bar_left)*val/mx
            d.text((bar_left-9,yy+bh/2),shorten(lab,23),font=font(14),fill=(55,63,68),anchor="rm")
            d.rectangle((bar_left,yy,xx,yy+bh),fill=(36,122,132))
            d.text((xx+4,yy+bh/2),f"{val:,}",font=font(13),fill=(60,70,75),anchor="lm")
    im.save(path)
def cramers_v(x,y):
    tab=pd.crosstab(x.fillna("(Missing)").astype(str),y.fillna("(Missing)").astype(str)).to_numpy(dtype=float)
    if min(tab.shape)<2:return np.nan,0
    n=tab.sum();expected=np.outer(tab.sum(1),tab.sum(0))/n
    with np.errstate(divide="ignore",invalid="ignore"):
        chi2=np.nansum(np.where(expected>0,(tab-expected)**2/expected,0))
    r,k=tab.shape;phi2=chi2/n
    phi2c=max(0,phi2-((k-1)*(r-1))/(n-1)) if n>1 else 0
    rc=r-((r-1)**2)/(n-1) if n>1 else r;kc=k-((k-1)**2)/(n-1) if n>1 else k
    denom=min(kc-1,rc-1);v=float(np.sqrt(phi2c/denom)) if denom>0 else np.nan
    return v,int((expected<5).sum())
def draw_heatmap(path,matrix):
    names=list(matrix.columns);abbr=[shorten(x,13) for x in names];cell=38;left=245;top=210
    im=Image.new("RGB",(left+len(names)*cell+35,top+len(names)*cell+50),"white");d=ImageDraw.Draw(im)
    d.text((25,20),"Association strength among predictors",font=font(27),fill=(18,48,74))
    d.text((27,58),"Bias-corrected Cramer's V; values range from 0 (weak) to 1 (strong)",font=font(16),fill=(80,90,98))
    for i,name in enumerate(names):
        y=top+i*cell
        d.text((left-10,y+cell/2),abbr[i],font=font(13),fill=(45,52,59),anchor="rm")
        for j in range(len(names)):
            v=matrix.iloc[i,j]
            if pd.isna(v):rgb=(235,235,235)
            else:
                v=max(0,min(1,float(v)));rgb=(int(246-190*v),int(250-125*v),int(248-30*v))
            d.rectangle((left+j*cell,y,left+(j+1)*cell-1,y+cell-1),fill=rgb,outline="white")
        # Render rotated column labels.
        lab=Image.new("RGBA",(100,20),(255,255,255,0));ld=ImageDraw.Draw(lab);ld.text((0,0),abbr[i],font=font(13),fill=(45,52,59))
        rot=lab.rotate(90,expand=True);im.paste(rot,(left+i*cell+9,top-rot.height-4),rot)
    im.save(path)

def main():
    ap=argparse.ArgumentParser(description="Generate Task 3 data-quality summaries and graphs.")
    ap.add_argument("--csv",default=None,help="Input dataset CSV; if omitted, scan the script folder")
    ap.add_argument("--output-dir",default=str(DEFAULT_OUT),help="Folder for evidence CSVs and PNGs")
    args=ap.parse_args();src=Path(args.csv).expanduser() if args.csv else discover_csv(Path(__file__).resolve().parent);out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    if not src.exists():raise FileNotFoundError(f"CSV not found: {src}. Supply --csv with the file location.")
    raw=pd.read_csv(src);df=raw.copy();n=len(df)
    if TARGET not in df:raise ValueError(f"Required label column {TARGET!r} was not found.")
    string_cols=df.select_dtypes(include=["object","string"]).columns.tolist()
    blank={c:int(raw[c].map(lambda v:isinstance(v,str) and v.strip()=="").sum()) for c in string_cols}
    trim={c:int(raw[c].map(lambda v:isinstance(v,str) and v!=v.strip()).sum()) for c in string_cols}
    for c in string_cols:df[c]=df[c].astype("string").str.strip()
    # Dataset feature definition: temperature values are ordered bands, not exact readings.
    if "temperature" in df:df["temperature"]=pd.Categorical(df["temperature"].map(TEMPERATURE_BANDS),categories=TEMPERATURE_ORDER,ordered=True)
    predictors=[c for c in df if c!=TARGET]

    # Overview, missingness, and duplicate diagnostics.
    overview=pd.DataFrame([("Rows",n,"One recorded offer/context per row."),("Columns",len(df.columns),"Includes predictors and Y."),("Candidate predictors",len(predictors),"All columns other than Y."),("Exact duplicate rows beyond first",int(df.duplicated().sum()),"Identical across every column."),("Rows with any missing field",int(df.isna().any(axis=1).sum()),"Incomplete records."),("Positive target rows",int((df[TARGET]==1).sum()),"Y=1, accepted."),("Negative target rows",int((df[TARGET]==0).sum()),"Y=0, not accepted.")],columns=["Metric","Value","Definition"])
    save_csv(overview,out,"01_overview.csv")
    missing=pd.DataFrame({"Feature":df.columns,"Missing_Count":df.isna().sum().values,"Missing_Percent":(100*df.isna().mean()).round(3).values}).sort_values("Missing_Count",ascending=False)
    save_csv(missing,out,"02_missingness.csv")
    exact=int(df.duplicated().sum());hashes=pd.util.hash_pandas_object(df[predictors].astype("string").fillna("<NA>"),index=False)
    lbl=pd.DataFrame({"hash":hashes,"Y":df[TARGET]}).groupby("hash",dropna=False).Y.nunique();conflict=set(lbl[lbl>1].index);conflict_rows=int(hashes.isin(conflict).sum())
    dup=pd.DataFrame([("Exact duplicate rows beyond first",exact,100*exact/n),("Rows with identical predictors but different Y",conflict_rows,100*conflict_rows/n),("Predictor patterns with conflicting Y",len(conflict),np.nan)],columns=["Measure","Count","Percent_of_rows"])
    save_csv(dup,out,"03_duplicates.csv")

    # Numeric summaries and skewness. IQR is eligible only for genuine continuous measurements.
    num=[c for c in df.select_dtypes(include=[np.number]).columns.tolist() if c!="temperature"]
    ns=df[num].describe().T;ns.index.name="Feature";save_csv(ns.reset_index(),out,"04_numeric_summary.csv")
    sk=[];outrows=[]
    for c in num:
        v=df[c].dropna().astype(float);uniq=set(v.unique());binary=uniq.issubset({0.,1.})
        skval=float(v.skew()) if v.nunique()>1 else np.nan
        note="Binary indicator/label: skewness reflects prevalence; use the class/frequency table." if binary else ("Numeric but recorded in only a few groups; interpret cautiously." if v.nunique()>1 else "Constant field; skewness undefined.")
        sk.append((c,len(v),v.nunique(),skval,note))
        if v.nunique()>2 and not binary:
            q1,q3=v.quantile(.25),v.quantile(.75);iqr=q3-q1;lo=q1-1.5*iqr;hi=q3+1.5*iqr;count=int(((v<lo)|(v>hi)).sum())
            outrows.append((c,len(v),v.nunique(),v.min(),v.max(),q1,q3,lo,hi,count,round(100*count/len(v),3),"IQR is only a screening flag; this feature is grouped, not a fine-grained measurement."))
    save_csv(pd.DataFrame(sk,columns=["Feature","Nonmissing_n","Unique_values","Skewness","Interpretation"]),out,"05_skewness.csv")
    outlier_cols=["Feature","Assessment","Nonmissing_n","Unique_values","Q1","Q3","IQR","Lower_Fence","Upper_Fence","Flagged_Count","Flagged_Percent","Notes"]
    if outrows:
        outlier_frame=pd.DataFrame([(r[0],"IQR screen applied",r[1],r[2],r[5],r[6],r[6]-r[5],r[7],r[8],r[9],r[10],r[11]) for r in outrows],columns=outlier_cols)
    else:
        outlier_frame=pd.DataFrame([("Dataset", "Not applicable - IQR not performed", np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, "No genuine continuous numeric predictors are present. Temperature is an ordinal category (30-54, 55-79, 80+); the remaining numeric fields are binary flags or the target. IQR fences would be meaningless.")],columns=outlier_cols)
    save_csv(outlier_frame,out,"06_outlier_assessment.csv")
    # Remove the old empty IQR-only report so it cannot be mistaken for current evidence.
    legacy_iqr=out/"06_outlier_iqr_screen.csv"
    if legacy_iqr.exists():
        try: legacy_iqr.unlink()
        except PermissionError: print(f"Close the obsolete file to remove it: {legacy_iqr}")

    # Complete category frequencies and compact feature summaries.
    freq=[];summ=[]
    for c in df:
        cnt=df[c].fillna("(Missing)").astype(str).value_counts(dropna=False)
        for val,k in cnt.items():freq.append((c,val,int(k),round(100*k/n,3)))
        summ.append((c,int(df[c].notna().sum()),int(df[c].nunique(dropna=True)),str(cnt.index[0]),int(cnt.iloc[0]),round(100*cnt.iloc[0]/n,3)))
    save_csv(pd.DataFrame(freq,columns=["Feature","Value","Count","Percent_of_all_rows"]),out,"07_feature_frequencies.csv")
    save_csv(pd.DataFrame(summ,columns=["Feature","Nonmissing_n","Unique_nonmissing","Most_common_value","Most_common_count_including_missing","Most_common_percent_of_rows"]),out,"08_feature_summary.csv")

    # Numeric correlations and categorical association strengths.
    nonconstant=[c for c in predictors if df[c].nunique(dropna=True)>1]
    vmat=pd.DataFrame(np.nan,index=nonconstant,columns=nonconstant);pairs=[]
    for i,a in enumerate(nonconstant):
        vmat.loc[a,a]=1.0
        for b in nonconstant[i+1:]:
            vv,sparse=cramers_v(df[a],df[b]);vmat.loc[a,b]=vmat.loc[b,a]=vv;pairs.append((a,b,vv,sparse))
    vmat.to_csv(out/"09_cramers_v_predictors.csv",encoding="utf-8-sig")
    save_csv(pd.DataFrame(pairs,columns=["Feature_1","Feature_2","Cramers_V_bias_corrected","Expected_cells_below_5"]).sort_values("Cramers_V_bias_corrected",ascending=False),out,"10_feature_associations.csv")
    targetrows=[]
    for c in predictors:
        vv,sparse=cramers_v(df[c],df[TARGET]);targetrows.append((c,vv,sparse,int(df[c].nunique(dropna=True))))
    targetassoc=pd.DataFrame(targetrows,columns=["Feature","Cramers_V_bias_corrected","Expected_cells_below_5","Unique_values"]).sort_values("Cramers_V_bias_corrected",ascending=False)
    save_csv(targetassoc,out,"11_target_associations.csv")
    validnum=[c for c in num if df[c].nunique(dropna=True)>1]
    df[validnum].corr(method="pearson").to_csv(out/"12_numeric_pearson_correlation.csv",encoding="utf-8-sig")
    df[validnum].corr(method="spearman").to_csv(out/"13_numeric_spearman_correlation.csv",encoding="utf-8-sig")

    # Target balance, rare-category review, possible noise, and consistency checks.
    cc=df[TARGET].value_counts(dropna=False).sort_index();balance=pd.DataFrame({"Y":cc.index.astype(str),"Count":cc.values,"Percent":(100*cc.values/n).round(3)})
    balance["Meaning"]=balance.Y.map({"0":"Not accepted","1":"Accepted"}).fillna("Missing/other");save_csv(balance,out,"14_class_balance.csv")
    rare=[]
    for c in df:
        counts=df[c].dropna().astype(str).value_counts()
        for value,k in counts.items():
            if 100*k/n<1:rare.append((c,value,int(k),round(100*k/n,3),"Review candidate only; rarity is not proof of error."))
    raredf=pd.DataFrame(rare,columns=["Feature","Value","Count","Percent_of_rows","Interpretation"]);save_csv(raredf,out,"15_rare_category_review_candidates.csv")
    noise=pd.DataFrame([("Exact duplicate rows",exact,"May be duplicates or repeated exposures; source provenance is needed."),("Predictor-identical rows with conflicting Y",conflict_rows,"Repeated predictor profile with differing outcome; may be a valid separate exposure or a recording issue, so source context is needed."),("Whitespace-only string cells",sum(blank.values()),"May encode missing values."),("String cells with leading/trailing whitespace",sum(trim.values()),"Can split semantically identical labels."),("Observed categories below 1% frequency",len(raredf),"Valid rare categories must not be removed automatically."),("Label noise verifiable from this CSV",0,"Cannot confirm incorrect labels without trusted outcome review or repeated adjudication.")],columns=["Indicator","Count","Interpretation"]);save_csv(noise,out,"16_noise_indicators.csv")
    inc=[]
    for c,allowed in DOMAINS.items():
        if c not in raw:continue
        obs=set(raw[c].dropna().tolist());bad=obs-allowed
        inc.append((c,int(raw[c].isna().sum()),trim.get(c,0),len(bad),"; ".join(map(str,sorted(bad,key=str)))[:500]))
    dviol=int(((df.direction_same+df.direction_opp)!=1).sum()) if {"direction_same","direction_opp"}.issubset(df.columns) else 0
    inc += [("direction_same + direction_opp",0,0,dviol,"Rows not summing to 1"),("Constant feature check: toCoupon_GEQ5min",0,0,int(df.toCoupon_GEQ5min.nunique(dropna=True)==1),"A constant value is low-information, not a data contradiction")]
    save_csv(pd.DataFrame(inc,columns=["Field_or_check","Missing_count","Whitespace_cells","Invalid_or_violation_count","Details"]),out,"17_inconsistency_checks.csv")

    # Charts produced with Pillow to keep the script lightweight and reproducible.
    miss=missing[missing.Missing_Count>0].sort_values("Missing_Percent")
    bar_chart(out/"figure_01_missingness.png","Missing values by feature",miss.Feature,miss.Missing_Percent,"Percent of all rows",width_px=1250,height_px=max(360,120+len(miss)*44),color=(181,93,67))
    bar_chart(out/"figure_02_class_balance.png","Coupon acceptance class balance",balance.Meaning,balance.Count,"Counts, with percentages in 14_class_balance.csv",width_px=1000,height_px=390)
    panels(out/"figure_03_offer_context_distributions.png","Offer and trip feature distributions",["coupon","destination","passanger","weather","time","expiration"],df)
    panels(out/"figure_04_profile_distributions.png","Driver profile feature distributions",["age","income","gender","maritalStatus","has_children","education"],df)
    occ=df.occupation.fillna("(Missing)").astype(str).value_counts().sort_values()
    bar_chart(out/"figure_05_occupation_distribution.png","Occupation category distribution",occ.index,occ.values,"All recorded occupation categories",width_px=1450,height_px=1000)
    panels(out/"figure_06_visit_frequency_distributions.png","Monthly venue-visit frequency distributions",VISITS,df,ncols=2)
    temp=df.temperature.value_counts().reindex(TEMPERATURE_ORDER,fill_value=0);bar_chart(out/"figure_07_temperature_distribution.png","Temperature band distribution",temp.index,temp.values,"Ordinal categories: 30-54, 55-79, and 80+",width_px=950,height_px=390,sort=False)
    draw_heatmap(out/"figure_08_cramers_v_heatmap.png",vmat)
    top=targetassoc.dropna(subset=["Cramers_V_bias_corrected"]).head(12).sort_values("Cramers_V_bias_corrected")
    bar_chart(out/"figure_09_target_association.png","Predictors with strongest unadjusted association with Y",top.Feature,top.Cramers_V_bias_corrected,"Bias-corrected Cramer's V; association is not causation",width_px=1300,height_px=620)
    print(f"Analyzed {n:,} rows and {len(df.columns)} columns. Evidence saved to: {out}")
    print(f"Exact duplicate rows={exact}; predictor-identical rows with conflicting Y={conflict_rows}")
    print(f"Y=1 rate={(df[TARGET]==1).mean():.3%}; majority/minority ratio={max(cc)/min(cc):.3f}:1")
    print("Missing values:\n",missing[missing.Missing_Count>0].to_string(index=False))
    if outrows:
        print("Outlier assessment: IQR screen applied to eligible continuous numeric predictors only.")
        print(outlier_frame[["Feature","Flagged_Count","Flagged_Percent","Lower_Fence","Upper_Fence"]].to_string(index=False))
    else:
        print("Outlier assessment: IQR not applicable; no continuous numeric predictors. Temperature is ordinal categorical (30-54, 55-79, 80+).")
    print("Top associations with Y:\n",targetassoc.head(8).to_string(index=False))

if __name__=="__main__":main()
