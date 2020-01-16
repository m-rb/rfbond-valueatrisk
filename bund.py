import pandas as pd
import numpy as np
from scipy.stats import norm
import QuantLib as ql
import sqlite3

bond_isin = 'DE0001102317'

sql_query = "SELECT * from rfRates"

conn = sqlite3.connect('rfRates.sqlite')
cur = conn.cursor()

df = pd.read_sql(sql_query, conn)
df = df.set_index('Date')

bp = df.diff(-1)[:-1] * 100

covariance = pd.DataFrame(np.cov(bp, rowvar=False),  ##shrinkage later
                          index=bp.columns,
                          columns=bp.columns)

todaysDate = ql.Date(4, 9, 2019)
ql.Settings.instance().evaluationDate = todaysDate

spotDates = [todaysDate,
             todaysDate + ql.Period(3, ql.Months),
             todaysDate + ql.Period(6, ql.Months),
             todaysDate + ql.Period(9, ql.Months),
             todaysDate + ql.Period(1, ql.Years),
             todaysDate + ql.Period(2, ql.Years),
             todaysDate + ql.Period(3, ql.Years),
             todaysDate + ql.Period(5, ql.Years),
             todaysDate + ql.Period(10, ql.Years),
             todaysDate + ql.Period(15, ql.Years),
             todaysDate + ql.Period(20, ql.Years),
             todaysDate + ql.Period(30, ql.Years),
             ]

spotRates = list(np.append(0, df[:1].values/100))   # todaysDate has 0 rate
dayCount = ql.Thirty360()
calendar = ql.Germany()
interpolation = ql.Linear()
compounding = ql.Continuous
compoundingFrequency = ql.Annual
spotCurve = ql.ZeroCurve(spotDates, spotRates, dayCount, calendar, interpolation, compounding, compoundingFrequency)
spotCurveHandle = ql.YieldTermStructureHandle(spotCurve)

issueDate = ql.Date(22, 6, 2010)
maturityDate = ql.Date(15, 5, 2049)
tenor = ql.Period(ql.Annual)
calendar = ql.Germany()
bussinessConvention = ql.Following
dateGeneration = ql.DateGeneration.Backward
monthEnd = False
schedule = ql.Schedule(issueDate, maturityDate, tenor, calendar, bussinessConvention,
                       bussinessConvention, dateGeneration, monthEnd)

dayCount = ql.ActualActual()
couponRate = .0150
coupons = [couponRate]

settlementDays = 2
faceValue = 1000000
fixedRateBond = ql.FixedRateBond(settlementDays, faceValue, schedule, coupons, dayCount)

bondEngine = ql.DiscountingBondEngine(spotCurveHandle)
fixedRateBond.setPricingEngine(bondEngine)

fixedRateBond.NPV()
original_npv = fixedRateBond.NPV()

for c in fixedRateBond.cashflows():
    print('%20s %12f' % (c.date(), c.amount()))

discount_handle = ql.RelinkableYieldTermStructureHandle(spotCurve)
fixedRateBond.setPricingEngine(ql.DiscountingBondEngine(discount_handle))

nodes = [i for i in spotRates]
dates = [j for j in spotDates]

spreads = [ql.SimpleQuote(0.0) for n in nodes]

new_curve = ql.SpreadedLinearZeroInterpolatedTermStructure(ql.YieldTermStructureHandle(spotCurve),
                                                           [ql.QuoteHandle(q) for q in spreads], dates)

discount_handle.linkTo(new_curve)

basis_point = 1.0e-4
key_risk = []
for i in range(1, len(spreads)):
    ref = 0.0
    spreads[i].setValue(ref - basis_point)
    print(fixedRateBond.NPV())
    key_risk.append(original_npv - fixedRateBond.NPV())
    spreads[i].setValue(ref)

pv01 = pd.DataFrame(-pd.to_numeric(key_risk), index=bp.columns) #(-)pv01

confidence_interval = 0.99
z_score = norm.ppf(confidence_interval)

bond_var = z_score * np.sqrt(pv01.T @ covariance @ pv01)
