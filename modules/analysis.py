import pandas as pd
from .data import AGE_ORDER,MONTHS
def monthly_trend(df):
    if df.empty: return pd.DataFrame(columns=["period","disease","cases"])
    x=df.groupby(["year_be","month","disease"],as_index=False).cases.sum()
    x["period"]=x.year_be.astype(str)+"-"+x.month.astype(str).str.zfill(2)
    return x[["period","disease","cases"]]
def age_summary(df,disease):
    x=df[df.disease==disease].groupby("age_group",as_index=False).cases.sum()
    x["age_group"]=pd.Categorical(x.age_group,categories=AGE_ORDER,ordered=True)
    return x.sort_values("age_group")
def next_month_forecast(df,disease):
    x=df[df.disease==disease].groupby(["year_be","month"],as_index=False).cases.sum().sort_values(["year_be","month"])
    if x.empty: return {"cases":0,"year_be":2569,"month_name":"ไม่พบข้อมูล"}
    last=x.iloc[-1]; y=int(last.year_be); m=int(last.month)+1
    if m>12: y+=1;m=1
    vals=x.cases.tail(3).tolist()
    estimate=round(sum(vals[i]*(i+1) for i in range(len(vals)))/sum(range(1,len(vals)+1)))
    return {"cases":max(0,int(estimate)),"year_be":y,"month_name":MONTHS[m-1]}
def kpi_summary(df):
    return {"cases":int(df.cases.sum()) if not df.empty else 0,"diseases":df.disease.nunique() if not df.empty else 0,"months":df.month.nunique() if not df.empty else 0}
