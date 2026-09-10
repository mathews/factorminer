[
  {
    "id": "gtja191_001",
    "nickname": null,
    "theme": [
      "volume",
      "reversal"
    ],
    "formula_latex": "(-1 * CORR(RANK(DELTA(LOG(VOLUME), 1)), RANK(((CLOSE - OPEN) / OPEN)), 6))",
    "columns_required": [
      "volume",
      "close",
      "open"
    ],
    "decay_horizon": 6,
    "min_warmup_bars": 7
  },
  {
    "id": "gtja191_002",
    "nickname": null,
    "theme": [
      "reversal",
      "microstructure"
    ],
    "formula_latex": "(-1 * DELTA(((CLOSE - LOW) - (HIGH - CLOSE)) / (HIGH - LOW), 1))",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 1,
    "min_warmup_bars": 2
  },
  {
    "id": "gtja191_003",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "SUM((CLOSE=DELAY(CLOSE,1)?0:CLOSE-(CLOSE>DELAY(CLOSE,1)?MIN(LOW,DELAY(CLOSE,1)):MAX(HIGH,DELAY(CLOSE,1)))),6)",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 6,
    "min_warmup_bars": 7
  },
  {
    "id": "gtja191_004",
    "nickname": null,
    "theme": [
      "momentum",
      "volume"
    ],
    "formula_latex": "((((SUM(CLOSE,8)/8)+STD(CLOSE,8))<(SUM(CLOSE,2)/2))?(-1):((SUM(CLOSE,2)/2<(SUM(CLOSE,8)/8-STD(CLOSE,8)))?1:((1<(VOLUME/MEAN(VOLUME,20)))?1:(-1))))",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 8,
    "min_warmup_bars": 20
  },
  {
    "id": "gtja191_005",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "(-1 * TSMAX(CORR(TSRANK(VOLUME,5), TSRANK(HIGH,5), 5), 3))",
    "columns_required": [
      "volume",
      "high"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 13
  },
  {
    "id": "gtja191_006",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "(RANK(SIGN(DELTA((OPEN*0.85+HIGH*0.15), 4))) * -1)",
    "columns_required": [
      "open",
      "high"
    ],
    "decay_horizon": 4,
    "min_warmup_bars": 5
  },
  {
    "id": "gtja191_007",
    "nickname": null,
    "theme": [
      "volume",
      "microstructure"
    ],
    "formula_latex": "((RANK(MAX((VWAP-CLOSE),3)) + RANK(MIN((VWAP-CLOSE),3))) * RANK(DELTA(VOLUME,3)))",
    "columns_required": [
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 3,
    "min_warmup_bars": 4
  },
  {
    "id": "gtja191_008",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "RANK(DELTA(((HIGH+LOW)/2)*0.2 + VWAP*0.8, 4)) * -1",
    "columns_required": [
      "high",
      "low",
      "volume",
      "amount"
    ],
    "decay_horizon": 4,
    "min_warmup_bars": 5
  },
  {
    "id": "gtja191_009",
    "nickname": null,
    "theme": [
      "volume",
      "microstructure"
    ],
    "formula_latex": "SMA(((HIGH+LOW)/2-(DELAY(HIGH,1)+DELAY(LOW,1))/2)*(HIGH-LOW)/VOLUME,7,2)",
    "columns_required": [
      "high",
      "low",
      "volume"
    ],
    "decay_horizon": 7,
    "min_warmup_bars": 8
  },
  {
    "id": "gtja191_010",
    "nickname": null,
    "theme": [
      "volatility",
      "reversal"
    ],
    "formula_latex": "RANK(MAX(((RET<0)?STD(RET,20):CLOSE)^2,5))",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_011",
    "nickname": null,
    "theme": [
      "volume",
      "microstructure"
    ],
    "formula_latex": "SUM(((CLOSE-LOW)-(HIGH-CLOSE))/(HIGH-LOW)*VOLUME,6)",
    "columns_required": [
      "close",
      "high",
      "low",
      "volume"
    ],
    "decay_horizon": 6,
    "min_warmup_bars": 7
  },
  {
    "id": "gtja191_012",
    "nickname": null,
    "theme": [
      "reversal",
      "microstructure"
    ],
    "formula_latex": "(RANK((OPEN - (SUM(VWAP,10)/10))) * (-1 * RANK(ABS((CLOSE - VWAP)))))",
    "columns_required": [
      "open",
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 10,
    "min_warmup_bars": 11
  },
  {
    "id": "gtja191_013",
    "nickname": null,
    "theme": [
      "microstructure"
    ],
    "formula_latex": "(((HIGH*LOW)^0.5) - VWAP)",
    "columns_required": [
      "high",
      "low",
      "volume",
      "amount"
    ],
    "decay_horizon": 1,
    "min_warmup_bars": 1
  },
  {
    "id": "gtja191_014",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "CLOSE - DELAY(CLOSE,5)",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 6
  },
  {
    "id": "gtja191_015",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "(OPEN/DELAY(CLOSE,1) - 1)",
    "columns_required": [
      "open",
      "close"
    ],
    "decay_horizon": 1,
    "min_warmup_bars": 2
  },
  {
    "id": "gtja191_016",
    "nickname": null,
    "theme": [
      "volume",
      "microstructure"
    ],
    "formula_latex": "(-1 * TSMAX(RANK(CORR(RANK(VOLUME), RANK(VWAP), 5)), 5))",
    "columns_required": [
      "volume",
      "amount"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 11
  },
  {
    "id": "gtja191_017",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "(RANK(VWAP - MAX(VWAP,15))^DELTA(CLOSE,5))",
    "columns_required": [
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 15,
    "min_warmup_bars": 16
  },
  {
    "id": "gtja191_018",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "CLOSE/DELAY(CLOSE,5)",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 6
  },
  {
    "id": "gtja191_019",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "(CLOSE<DELAY(CLOSE,5)?(CLOSE-DELAY(CLOSE,5))/DELAY(CLOSE,5):(CLOSE=DELAY(CLOSE,5)?0:(CLOSE-DELAY(CLOSE,5))/CLOSE))",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 6
  },
  {
    "id": "gtja191_020",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "((CLOSE-DELAY(CLOSE,6))/DELAY(CLOSE,6))*100",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 6,
    "min_warmup_bars": 7
  },
  {
    "id": "gtja191_021",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "REGBETA(MEAN(CLOSE,6), SEQUENCE(6))",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 6,
    "min_warmup_bars": 12
  },
  {
    "id": "gtja191_022",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "SMA(((CLOSE-MEAN(CLOSE,6))/MEAN(CLOSE,6) - DELAY((CLOSE-MEAN(CLOSE,6))/MEAN(CLOSE,6),3)),12,1)",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 10
  },
  {
    "id": "gtja191_023",
    "nickname": null,
    "theme": [
      "volatility"
    ],
    "formula_latex": "SMA((CLOSE>DELAY(CLOSE,1)?STD(CLOSE,20):0),20,1)/(SMA((CLOSE>DELAY(CLOSE,1)?STD(CLOSE,20):0),20,1) + SMA((CLOSE<=DELAY(CLOSE,1)?STD(CLOSE,20):0),20,1)) * 100",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 22
  },
  {
    "id": "gtja191_024",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "SMA(CLOSE-DELAY(CLOSE,5),5,1)",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 6
  },
  {
    "id": "gtja191_025",
    "nickname": null,
    "theme": [
      "momentum",
      "volume"
    ],
    "formula_latex": "((-1*RANK((DELTA(CLOSE,7)*(1-RANK(DECAYLINEAR((VOLUME/MEAN(VOLUME,20)),9))))))*(1+RANK(SUM(RET,250))))",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 9,
    "min_warmup_bars": 61
  },
  {
    "id": "gtja191_026",
    "nickname": null,
    "theme": [
      "momentum",
      "microstructure"
    ],
    "formula_latex": "((((SUM(CLOSE,7)/7)-CLOSE))+((CORR(VWAP,DELAY(CLOSE,5),230))))",
    "columns_required": [
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 7,
    "min_warmup_bars": 35
  },
  {
    "id": "gtja191_027",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "WMA((CLOSE-DELAY(CLOSE,3))/DELAY(CLOSE,3)*100 + (CLOSE-DELAY(CLOSE,6))/DELAY(CLOSE,6)*100, 12)",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 18
  },
  {
    "id": "gtja191_028",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "3*SMA((CLOSE-TSMIN(LOW,9))/(TSMAX(HIGH,9)-TSMIN(LOW,9))*100,3,1)-2*SMA(SMA((CLOSE-TSMIN(LOW,9))/(TSMAX(HIGH,9)-TSMIN(LOW,9))*100,3,1),3,1)",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 9,
    "min_warmup_bars": 12
  },
  {
    "id": "gtja191_029",
    "nickname": null,
    "theme": [
      "momentum",
      "volume"
    ],
    "formula_latex": "(CLOSE-DELAY(CLOSE,6))/DELAY(CLOSE,6)*VOLUME",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 6,
    "min_warmup_bars": 7
  },
  {
    "id": "gtja191_030",
    "nickname": null,
    "theme": [
      "volatility"
    ],
    "formula_latex": "WMA((REGRESI(CLOSE/DELAY(CLOSE,1)-1, MKT_RET, SMB, HML, 60))^2, 20)",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_031",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "(CLOSE-MEAN(CLOSE,12))/MEAN(CLOSE,12)*100",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 13
  },
  {
    "id": "gtja191_032",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "(-1 * SUM(RANK(CORR(RANK(HIGH), RANK(VOLUME), 3)), 3))",
    "columns_required": [
      "high",
      "volume"
    ],
    "decay_horizon": 3,
    "min_warmup_bars": 7
  },
  {
    "id": "gtja191_033",
    "nickname": null,
    "theme": [
      "momentum",
      "volume"
    ],
    "formula_latex": "((((-1*TSMIN(LOW,5))+DELAY(TSMIN(LOW,5),5))*RANK(((SUM(RET,240)-SUM(RET,20))/220)))*TSRANK(VOLUME,5))",
    "columns_required": [
      "low",
      "close",
      "volume"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 61
  },
  {
    "id": "gtja191_034",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "MEAN(CLOSE,12)/CLOSE",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 13
  },
  {
    "id": "gtja191_035",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "(MIN(RANK(DECAYLINEAR(DELTA(OPEN,1),15)), RANK(DECAYLINEAR(CORR(VOLUME,((OPEN*0.65)+(OPEN*0.35)),17),7))) * -1)",
    "columns_required": [
      "open",
      "volume"
    ],
    "decay_horizon": 15,
    "min_warmup_bars": 25
  },
  {
    "id": "gtja191_036",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "RANK(SUM(CORR(RANK(VOLUME), RANK(VWAP), 6), 2))",
    "columns_required": [
      "volume",
      "amount"
    ],
    "decay_horizon": 6,
    "min_warmup_bars": 8
  },
  {
    "id": "gtja191_037",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "(-1*RANK(((SUM(OPEN,5)*SUM(RET,5))-DELAY((SUM(OPEN,5)*SUM(RET,5)),10))))",
    "columns_required": [
      "open",
      "close"
    ],
    "decay_horizon": 10,
    "min_warmup_bars": 16
  },
  {
    "id": "gtja191_038",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "(((SUM(HIGH,20)/20)<HIGH)?(-1*DELTA(HIGH,2)):0)",
    "columns_required": [
      "high"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_039",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "((RANK(DECAYLINEAR(DELTA(CLOSE,2),8)) - RANK(DECAYLINEAR(CORR(((VWAP*0.3)+(OPEN*0.7)),SUM(MEAN(VOLUME,180),37),14),12)))*-1)",
    "columns_required": [
      "close",
      "open",
      "volume",
      "amount"
    ],
    "decay_horizon": 14,
    "min_warmup_bars": 63
  },
  {
    "id": "gtja191_040",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "SUM((CLOSE>DELAY(CLOSE,1)?VOLUME:0),26)/SUM((CLOSE<=DELAY(CLOSE,1)?VOLUME:0),26)*100",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 26,
    "min_warmup_bars": 27
  },
  {
    "id": "gtja191_041",
    "nickname": null,
    "theme": [
      "microstructure"
    ],
    "formula_latex": "(RANK(MAX(DELTA(VWAP,3),5))*-1)",
    "columns_required": [
      "volume",
      "amount"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 9
  },
  {
    "id": "gtja191_042",
    "nickname": null,
    "theme": [
      "volume",
      "volatility"
    ],
    "formula_latex": "((-1*RANK(STD(HIGH,10)))*CORR(HIGH,VOLUME,10))",
    "columns_required": [
      "high",
      "volume"
    ],
    "decay_horizon": 10,
    "min_warmup_bars": 11
  },
  {
    "id": "gtja191_043",
    "nickname": null,
    "theme": [
      "volume",
      "momentum"
    ],
    "formula_latex": "SUM((CLOSE>DELAY(CLOSE,1)?VOLUME:(CLOSE<DELAY(CLOSE,1)?-VOLUME:0)),6)",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 6,
    "min_warmup_bars": 7
  },
  {
    "id": "gtja191_044",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "(TSRANK(DECAYLINEAR(CORR(LOW,MEAN(VOLUME,10),7),6),4)+TSRANK(DECAYLINEAR(DELTA(VWAP,3),10),15))",
    "columns_required": [
      "low",
      "volume",
      "amount"
    ],
    "decay_horizon": 10,
    "min_warmup_bars": 27
  },
  {
    "id": "gtja191_045",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "(RANK(DELTA((((CLOSE*0.6)+(OPEN*0.4))),1)) * RANK(CORR(VWAP,MEAN(VOLUME,150),15)))",
    "columns_required": [
      "close",
      "open",
      "volume",
      "amount"
    ],
    "decay_horizon": 15,
    "min_warmup_bars": 44
  },
  {
    "id": "gtja191_046",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "(MEAN(CLOSE,3)+MEAN(CLOSE,6)+MEAN(CLOSE,12)+MEAN(CLOSE,24))/(4*CLOSE)",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 24,
    "min_warmup_bars": 25
  },
  {
    "id": "gtja191_047",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "SMA((TSMAX(HIGH,6)-CLOSE)/(TSMAX(HIGH,6)-TSMIN(LOW,6))*100,9,1)",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 9,
    "min_warmup_bars": 10
  },
  {
    "id": "gtja191_048",
    "nickname": null,
    "theme": [
      "volume",
      "momentum"
    ],
    "formula_latex": "-1*((RANK((SIGN((CLOSE-DELAY(CLOSE,1)))+SIGN((DELAY(CLOSE,1)-DELAY(CLOSE,2)))+SIGN((DELAY(CLOSE,2)-DELAY(CLOSE,3))))))*SUM(VOLUME,5))/SUM(VOLUME,20)",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_049",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "SUM(((HIGH+LOW)>=(DELAY(HIGH,1)+DELAY(LOW,1))?0:MAX(ABS(HIGH-DELAY(HIGH,1)),ABS(LOW-DELAY(LOW,1)))),12)/(SUM(...,12)+SUM(...,12))",
    "columns_required": [
      "high",
      "low"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 13
  },
  {
    "id": "gtja191_050",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "SUM(up_move,12)/(SUM(up_move,12)+SUM(dn_move,12)) - SUM(dn_move,12)/(SUM(up_move,12)+SUM(dn_move,12))",
    "columns_required": [
      "high",
      "low"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 13
  },
  {
    "id": "gtja191_051",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "SUM(up_move,12)/(SUM(up_move,12)+SUM(dn_move,12))",
    "columns_required": [
      "high",
      "low"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 13
  },
  {
    "id": "gtja191_052",
    "nickname": null,
    "theme": [
      "microstructure"
    ],
    "formula_latex": "SUM(MAX(0,HIGH-DELAY((HIGH+LOW+CLOSE)/3,1)),26) / SUM(MAX(0,DELAY((HIGH+LOW+CLOSE)/3,1)-LOW),26) * 100",
    "columns_required": [
      "high",
      "low",
      "close"
    ],
    "decay_horizon": 26,
    "min_warmup_bars": 27
  },
  {
    "id": "gtja191_053",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "COUNT(CLOSE>DELAY(CLOSE,1),12)/12*100",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 13
  },
  {
    "id": "gtja191_054",
    "nickname": null,
    "theme": [
      "volatility",
      "microstructure"
    ],
    "formula_latex": "((-1*RANK((STD(ABS(CLOSE-OPEN),10)+(CLOSE-OPEN))+CORR(CLOSE,OPEN,10))))",
    "columns_required": [
      "close",
      "open"
    ],
    "decay_horizon": 10,
    "min_warmup_bars": 11
  },
  {
    "id": "gtja191_055",
    "nickname": null,
    "theme": [
      "microstructure"
    ],
    "formula_latex": "SUM(16*(CLOSE-DELAY(CLOSE,1)+(CLOSE-OPEN)/2+DELAY(CLOSE,1)-DELAY(OPEN,1))/((ABS(HIGH-DELAY(CLOSE,1))>ABS(LOW-DELAY(CLOSE,1)) && ABS(HIGH-DELAY(CLOSE,1))>ABS(HIGH-DELAY(LOW,1))?ABS(HIGH-DELAY(CLOSE,1))+ABS(LOW-DELAY(CLOSE,1))/2+ABS(DELAY(CLOSE,1)-DELAY(OPEN,1))/4:ABS(LOW-DELAY(CLOSE,1))+ABS(HIGH-DELAY(CLOSE,1))/2+ABS(DELAY(CLOSE,1)-DELAY(OPEN,1))/4))*MAX(ABS(HIGH-DELAY(CLOSE,1)),ABS(LOW-DELAY(CLOSE,1))),20)",
    "columns_required": [
      "close",
      "high",
      "low",
      "open"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 22
  },
  {
    "id": "gtja191_056",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "(RANK(OPEN-TSMIN(OPEN,12)) < RANK((RANK(CORR(SUM(((HIGH+LOW)/2),19),SUM(MEAN(VOLUME,40),19),13))^5)))",
    "columns_required": [
      "open",
      "high",
      "low",
      "volume"
    ],
    "decay_horizon": 19,
    "min_warmup_bars": 60
  },
  {
    "id": "gtja191_057",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "SMA((CLOSE-TSMIN(LOW,9))/(TSMAX(HIGH,9)-TSMIN(LOW,9))*100,3,1)",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 9,
    "min_warmup_bars": 10
  },
  {
    "id": "gtja191_058",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "COUNT(CLOSE>DELAY(CLOSE,1),20)/20*100",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_059",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "SUM((CLOSE=DELAY(CLOSE,1)?0:CLOSE-(CLOSE>DELAY(CLOSE,1)?MIN(LOW,DELAY(CLOSE,1)):MAX(HIGH,DELAY(CLOSE,1)))),20)",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 22
  },
  {
    "id": "gtja191_060",
    "nickname": null,
    "theme": [
      "volume",
      "microstructure"
    ],
    "formula_latex": "SUM(((CLOSE-LOW)-(HIGH-CLOSE))/(HIGH-LOW)*VOLUME, 20)",
    "columns_required": [
      "close",
      "high",
      "low",
      "volume"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_061",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "(MAX(RANK(DECAYLINEAR(DELTA(VWAP,1),12)), RANK(DECAYLINEAR(RANK(CORR(LOW,MEAN(VOLUME,80),8)),17))) * -1)",
    "columns_required": [
      "volume",
      "amount",
      "low"
    ],
    "decay_horizon": 17,
    "min_warmup_bars": 53
  },
  {
    "id": "gtja191_062",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "((-1*CORR(HIGH,RANK(VOLUME),5)))",
    "columns_required": [
      "high",
      "volume"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 6
  },
  {
    "id": "gtja191_063",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "SMA(MAX(CLOSE-DELAY(CLOSE,1),0),6,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),6,1)*100",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 6,
    "min_warmup_bars": 7
  },
  {
    "id": "gtja191_064",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "(MAX(RANK(DECAYLINEAR(CORR(RANK(VWAP),RANK(VOLUME),4),4)),RANK(DECAYLINEAR(MAX(CORR(RANK(CLOSE),RANK(MEAN(VOLUME,60)),4),13),14)))*-1)",
    "columns_required": [
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 14,
    "min_warmup_bars": 30
  },
  {
    "id": "gtja191_065",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "MEAN(CLOSE,6)/CLOSE",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 6,
    "min_warmup_bars": 7
  },
  {
    "id": "gtja191_066",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "(CLOSE-MEAN(CLOSE,6))/MEAN(CLOSE,6)*100",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 6,
    "min_warmup_bars": 7
  },
  {
    "id": "gtja191_067",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "SMA(MAX(CLOSE-DELAY(CLOSE,1),0),24,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),24,1)*100",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 24,
    "min_warmup_bars": 25
  },
  {
    "id": "gtja191_068",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "SMA(((HIGH+LOW)/2-(DELAY(HIGH,1)+DELAY(LOW,1))/2)*(HIGH-LOW)/VOLUME,15,2)",
    "columns_required": [
      "high",
      "low",
      "volume"
    ],
    "decay_horizon": 15,
    "min_warmup_bars": 16
  },
  {
    "id": "gtja191_069",
    "nickname": null,
    "theme": [
      "microstructure"
    ],
    "formula_latex": "(SUM(DTM,20)>SUM(DBM,20)?(SUM(DTM,20)-SUM(DBM,20))/SUM(DTM,20):(SUM(DTM,20)=SUM(DBM,20)?0:(SUM(DTM,20)-SUM(DBM,20))/SUM(DBM,20)))",
    "columns_required": [
      "open",
      "high",
      "low"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 22
  },
  {
    "id": "gtja191_070",
    "nickname": null,
    "theme": [
      "volatility",
      "volume"
    ],
    "formula_latex": "STD(AMOUNT,6)",
    "columns_required": [
      "amount"
    ],
    "decay_horizon": 6,
    "min_warmup_bars": 7
  },
  {
    "id": "gtja191_071",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "(CLOSE-MEAN(CLOSE,24))/MEAN(CLOSE,24)*100",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 24,
    "min_warmup_bars": 25
  },
  {
    "id": "gtja191_072",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "SMA((TSMAX(HIGH,6)-CLOSE)/(TSMAX(HIGH,6)-TSMIN(LOW,6))*100,15,1)",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 15,
    "min_warmup_bars": 16
  },
  {
    "id": "gtja191_073",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "((TSRANK(DECAYLINEAR(DECAYLINEAR(CORR((CLOSE),VOLUME,10),16),4),5) - RANK(DECAYLINEAR(CORR(VWAP,MEAN(VOLUME,30),4),3))) * -1)",
    "columns_required": [
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 16,
    "min_warmup_bars": 35
  },
  {
    "id": "gtja191_074",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "(RANK(CORR(SUM(((LOW*0.35)+(VWAP*0.65)),20),SUM(MEAN(VOLUME,40),20),7)) + RANK(CORR(RANK(VWAP),RANK(VOLUME),6)))",
    "columns_required": [
      "low",
      "volume",
      "amount"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 30
  },
  {
    "id": "gtja191_075",
    "nickname": null,
    "theme": [
      "sentiment",
      "momentum"
    ],
    "formula_latex": "COUNT((CLOSE>OPEN & BENCHMARKINDEXCLOSE<DELAY(BENCHMARKINDEXCLOSE,1)),50)/COUNT(BENCHMARKINDEXCLOSE<DELAY(BENCHMARKINDEXCLOSE,1),50)",
    "columns_required": [
      "close",
      "open"
    ],
    "decay_horizon": 50,
    "min_warmup_bars": 30
  },
  {
    "id": "gtja191_076",
    "nickname": null,
    "theme": [
      "volatility",
      "volume"
    ],
    "formula_latex": "STD(ABS((CLOSE/DELAY(CLOSE,1)-1))/VOLUME,20)/MEAN(ABS((CLOSE/DELAY(CLOSE,1)-1))/VOLUME,20)",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 22
  },
  {
    "id": "gtja191_077",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "MIN(RANK(DECAYLINEAR(((HIGH+LOW)/2+HIGH-(VWAP+HIGH)),20)),RANK(DECAYLINEAR(CORR(((HIGH+LOW)/2),MEAN(VOLUME,40),3),6)))",
    "columns_required": [
      "high",
      "low",
      "volume",
      "amount"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 37
  },
  {
    "id": "gtja191_078",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "((HIGH+LOW+CLOSE)/3-MA((HIGH+LOW+CLOSE)/3,12))/(0.015*MEAN(ABS(CLOSE-MA((HIGH+LOW+CLOSE)/3,12)),12))",
    "columns_required": [
      "high",
      "low",
      "close"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 23
  },
  {
    "id": "gtja191_079",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "SMA(MAX(CLOSE-DELAY(CLOSE,1),0),12,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),12,1)*100",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 13
  },
  {
    "id": "gtja191_080",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "(VOLUME-DELAY(VOLUME,5))/DELAY(VOLUME,5)*100",
    "columns_required": [
      "volume"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 6
  },
  {
    "id": "gtja191_081",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "SMA(VOLUME,21,2)",
    "columns_required": [
      "volume"
    ],
    "decay_horizon": 21,
    "min_warmup_bars": 22
  },
  {
    "id": "gtja191_082",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "SMA((TSMAX(HIGH,6)-CLOSE)/(TSMAX(HIGH,6)-TSMIN(LOW,6))*100,20,1)",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_083",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "(-1*RANK(COVIANCE(RANK(HIGH),RANK(VOLUME),5)))",
    "columns_required": [
      "high",
      "volume"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 6
  },
  {
    "id": "gtja191_084",
    "nickname": null,
    "theme": [
      "volume",
      "momentum"
    ],
    "formula_latex": "SUM(CLOSE>DELAY(CLOSE,1)?VOLUME:(CLOSE<DELAY(CLOSE,1)?-VOLUME:0),20)",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_085",
    "nickname": null,
    "theme": [
      "volume",
      "momentum"
    ],
    "formula_latex": "(TSRANK((VOLUME/MEAN(VOLUME,20)),20)*TSRANK((-1*DELTA(CLOSE,7)),8))",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 39
  },
  {
    "id": "gtja191_086",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "((0.25 < (((DELAY(CLOSE,20)-DELAY(CLOSE,10))/10) - ((DELAY(CLOSE,10)-CLOSE)/10))) ? -1 : (((((DELAY(CLOSE,20)-DELAY(CLOSE,10))/10) - ((DELAY(CLOSE,10)-CLOSE)/10)) < 0) ? 1 : (-1*(CLOSE-DELAY(CLOSE,1)))))",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 22
  },
  {
    "id": "gtja191_087",
    "nickname": null,
    "theme": [
      "microstructure"
    ],
    "formula_latex": "((RANK(DECAYLINEAR(DELTA(VWAP,4),7))+TSRANK(DECAYLINEAR((((LOW*0.9)+(LOW*0.1))-VWAP)/(OPEN-((HIGH+LOW)/2)),11),7))*-1)",
    "columns_required": [
      "close",
      "open",
      "high",
      "low",
      "volume",
      "amount"
    ],
    "decay_horizon": 11,
    "min_warmup_bars": 22
  },
  {
    "id": "gtja191_088",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "(CLOSE-DELAY(CLOSE,20))/DELAY(CLOSE,20)*100",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_089",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "2*(SMA(CLOSE,13,2)-SMA(CLOSE,27,2)-SMA(SMA(CLOSE,13,2)-SMA(CLOSE,27,2),10,2))",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 27,
    "min_warmup_bars": 28
  },
  {
    "id": "gtja191_090",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "((-1*RANK(CORR(RANK(VWAP),RANK(VOLUME),5))))",
    "columns_required": [
      "volume",
      "amount"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 6
  },
  {
    "id": "gtja191_091",
    "nickname": null,
    "theme": [
      "volume",
      "reversal"
    ],
    "formula_latex": "((-1*RANK((CLOSE-MAX(CLOSE,5))))*RANK(CORR(MEAN(VOLUME,40),LOW,5)))",
    "columns_required": [
      "close",
      "low",
      "volume"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 35
  },
  {
    "id": "gtja191_092",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "(MAX(RANK(DECAYLINEAR(DELTA(((CLOSE*0.35)+(VWAP*0.65)),2),3)),TSRANK(DECAYLINEAR(ABS(CORR(MEAN(VOLUME,180),CLOSE,13)),5),15))*-1)",
    "columns_required": [
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 15,
    "min_warmup_bars": 60
  },
  {
    "id": "gtja191_093",
    "nickname": null,
    "theme": [
      "microstructure"
    ],
    "formula_latex": "SUM((OPEN>=DELAY(OPEN,1)?0:MAX(OPEN-LOW,OPEN-DELAY(OPEN,1))),20)",
    "columns_required": [
      "open",
      "low"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 22
  },
  {
    "id": "gtja191_094",
    "nickname": null,
    "theme": [
      "volume",
      "momentum"
    ],
    "formula_latex": "SUM(CLOSE>DELAY(CLOSE,1)?VOLUME:(CLOSE<DELAY(CLOSE,1)?-VOLUME:0),30)",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 30,
    "min_warmup_bars": 31
  },
  {
    "id": "gtja191_095",
    "nickname": null,
    "theme": [
      "volatility",
      "volume"
    ],
    "formula_latex": "STD(AMOUNT,20)",
    "columns_required": [
      "amount"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_096",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "SMA(SMA((CLOSE-TSMIN(LOW,9))/(TSMAX(HIGH,9)-TSMIN(LOW,9))*100,3,1),3,1)",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 9,
    "min_warmup_bars": 12
  },
  {
    "id": "gtja191_097",
    "nickname": null,
    "theme": [
      "volatility",
      "volume"
    ],
    "formula_latex": "STD(VOLUME,10)",
    "columns_required": [
      "volume"
    ],
    "decay_horizon": 10,
    "min_warmup_bars": 11
  },
  {
    "id": "gtja191_098",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "((((DELTA((SUM(CLOSE,100)/100),100)/DELAY(CLOSE,100))<0.05) || ((DELTA((SUM(CLOSE,100)/100),100)/DELAY(CLOSE,100))==0.05)) ? (-1*(CLOSE-TSMIN(CLOSE,100))) : (-1*DELTA(CLOSE,3)))",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 30,
    "min_warmup_bars": 60
  },
  {
    "id": "gtja191_099",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "(-1*RANK(COVIANCE(RANK(CLOSE),RANK(VOLUME),5)))",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 6
  },
  {
    "id": "gtja191_100",
    "nickname": null,
    "theme": [
      "volatility",
      "volume"
    ],
    "formula_latex": "STD(VOLUME,20)",
    "columns_required": [
      "volume"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_101",
    "nickname": null,
    "theme": [
      "volume",
      "momentum"
    ],
    "formula_latex": "((rank(ts\\_corr(close, sum(ts\\_mean(volume,30),37), 15)) < rank(ts\\_corr(rank(high), rank(ts\\_mean(volume,10)), 11))) * -1)",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 15,
    "min_warmup_bars": 80
  },
  {
    "id": "gtja191_102",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "sma(max(volume-delay(volume,1),0),6,1)/sma(abs(volume-delay(volume,1)),6,1)*100",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 6,
    "min_warmup_bars": 7
  },
  {
    "id": "gtja191_103",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "((20-lowday(low,20))/20)*100",
    "columns_required": [
      "close",
      "low"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 20
  },
  {
    "id": "gtja191_104",
    "nickname": null,
    "theme": [
      "volume",
      "volatility"
    ],
    "formula_latex": "-1*delta(corr(high,volume,5),5)*rank(std(close,20))",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 25
  },
  {
    "id": "gtja191_105",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "-1*corr(rank(open),rank(volume),10)",
    "columns_required": [
      "open",
      "volume",
      "close"
    ],
    "decay_horizon": 10,
    "min_warmup_bars": 10
  },
  {
    "id": "gtja191_106",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "close-delay(close,20)",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_107",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "-1*rank(open-delay(high,1))*rank(open-delay(close,1))*rank(open-delay(low,1))",
    "columns_required": [
      "open",
      "high",
      "low",
      "close"
    ],
    "decay_horizon": 1,
    "min_warmup_bars": 2
  },
  {
    "id": "gtja191_108",
    "nickname": null,
    "theme": [
      "reversal",
      "volume"
    ],
    "formula_latex": "(rank(high-min(high,2))^rank(corr(vwap,mean(volume,120),6)))*-1",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 6,
    "min_warmup_bars": 125
  },
  {
    "id": "gtja191_109",
    "nickname": null,
    "theme": [
      "volatility"
    ],
    "formula_latex": "sma(high-low,10,2)/sma(sma(high-low,10,2),10,2)",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 10,
    "min_warmup_bars": 20
  },
  {
    "id": "gtja191_110",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "sum(max(0,high-delay(close,1)),20)/sum(max(0,delay(close,1)-low),20)*100",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_111",
    "nickname": null,
    "theme": [
      "volume",
      "microstructure"
    ],
    "formula_latex": "sma(v*((c-l)-(h-c))/(h-l),11,2)-sma(v*((c-l)-(h-c))/(h-l),4,2)",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume"
    ],
    "decay_horizon": 11,
    "min_warmup_bars": 12
  },
  {
    "id": "gtja191_112",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "(sum_up(12)-sum_down(12))/(sum_up(12)+sum_down(12))*100",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 13
  },
  {
    "id": "gtja191_113",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "-1*(rank(mean(delay(c,5),20))*corr(c,v,2))*rank(corr(sum(c,5),sum(c,20),2))",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 27
  },
  {
    "id": "gtja191_114",
    "nickname": null,
    "theme": [
      "volume",
      "volatility"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 7
  },
  {
    "id": "gtja191_115",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "rank(corr(0.9h+0.1c,mean(v,30),10))^rank(corr(tsrank((h+l)/2,4),tsrank(v,10),7))",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume"
    ],
    "decay_horizon": 30,
    "min_warmup_bars": 40
  },
  {
    "id": "gtja191_116",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "regbeta(close,sequence(20),20)",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 20
  },
  {
    "id": "gtja191_117",
    "nickname": null,
    "theme": [
      "volume",
      "momentum"
    ],
    "formula_latex": "tsrank(v,32)*(1-tsrank(c+h-l,16))*(1-tsrank(ret,32))",
    "columns_required": [
      "close",
      "high",
      "low",
      "volume"
    ],
    "decay_horizon": 32,
    "min_warmup_bars": 33
  },
  {
    "id": "gtja191_118",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "sum(h-o,20)/sum(o-l,20)*100",
    "columns_required": [
      "open",
      "high",
      "low",
      "close"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 20
  },
  {
    "id": "gtja191_119",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 26,
    "min_warmup_bars": 60
  },
  {
    "id": "gtja191_120",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "rank(vwap-close)/rank(vwap+close)",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 1,
    "min_warmup_bars": 1
  },
  {
    "id": "gtja191_121",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 60,
    "min_warmup_bars": 80
  },
  {
    "id": "gtja191_122",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 13,
    "min_warmup_bars": 40
  },
  {
    "id": "gtja191_123",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume"
    ],
    "decay_horizon": 60,
    "min_warmup_bars": 90
  },
  {
    "id": "gtja191_124",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "(close-vwap)/decay_linear(rank(tsmax(close,30)),2)",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 30,
    "min_warmup_bars": 32
  },
  {
    "id": "gtja191_125",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 60,
    "min_warmup_bars": 120
  },
  {
    "id": "gtja191_126",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "(c+h+l)/3",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 1,
    "min_warmup_bars": 1
  },
  {
    "id": "gtja191_127",
    "nickname": null,
    "theme": [
      "volatility"
    ],
    "formula_latex": "sqrt(mean((100*(c-tsmax(c,12))/tsmax(c,12))^2,12))",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 24
  },
  {
    "id": "gtja191_128",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume"
    ],
    "decay_horizon": 14,
    "min_warmup_bars": 16
  },
  {
    "id": "gtja191_129",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "sum(abs(c-delay(c,1)) if dc<0 else 0,12)",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 13
  },
  {
    "id": "gtja191_130",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 40,
    "min_warmup_bars": 60
  },
  {
    "id": "gtja191_131",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "rank(delta(vwap,1))^tsrank(corr(close,mean(v,50),18),18)",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 50,
    "min_warmup_bars": 84
  },
  {
    "id": "gtja191_132",
    "nickname": null,
    "theme": [
      "liquidity"
    ],
    "formula_latex": "mean(amount,20)",
    "columns_required": [
      "close",
      "amount"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 20
  },
  {
    "id": "gtja191_133",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "((20-highday(high,20))/20)*100-((20-lowday(low,20))/20)*100",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 20
  },
  {
    "id": "gtja191_134",
    "nickname": null,
    "theme": [
      "momentum",
      "volume"
    ],
    "formula_latex": "(close-delay(close,12))/delay(close,12)*volume",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 13
  },
  {
    "id": "gtja191_135",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "sma(delay(c/delay(c,20),1),20,1)",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 22
  },
  {
    "id": "gtja191_136",
    "nickname": null,
    "theme": [
      "momentum",
      "volume"
    ],
    "formula_latex": "-1*rank(delta(ret,3))*corr(open,volume,10)",
    "columns_required": [
      "open",
      "close",
      "volume"
    ],
    "decay_horizon": 10,
    "min_warmup_bars": 11
  },
  {
    "id": "gtja191_137",
    "nickname": null,
    "theme": [
      "volatility"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high",
      "low",
      "close"
    ],
    "decay_horizon": 1,
    "min_warmup_bars": 2
  },
  {
    "id": "gtja191_138",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 60,
    "min_warmup_bars": 119
  },
  {
    "id": "gtja191_139",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "-1*corr(open,volume,10)",
    "columns_required": [
      "open",
      "volume",
      "close"
    ],
    "decay_horizon": 10,
    "min_warmup_bars": 10
  },
  {
    "id": "gtja191_140",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume"
    ],
    "decay_horizon": 60,
    "min_warmup_bars": 100
  },
  {
    "id": "gtja191_141",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "rank(corr(rank(high),rank(mean(v,15)),9))*-1",
    "columns_required": [
      "high",
      "volume",
      "close"
    ],
    "decay_horizon": 15,
    "min_warmup_bars": 24
  },
  {
    "id": "gtja191_142",
    "nickname": null,
    "theme": [
      "volume",
      "reversal"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 26
  },
  {
    "id": "gtja191_143",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "cumprod(1 + (c/delay(c,1)-1) if c>delay(c,1) else 0)",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 1,
    "min_warmup_bars": 2
  },
  {
    "id": "gtja191_144",
    "nickname": null,
    "theme": [
      "liquidity"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "close",
      "amount"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_145",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "(mean(v,9)-mean(v,26))/mean(v,12)*100",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 26,
    "min_warmup_bars": 26
  },
  {
    "id": "gtja191_146",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 60,
    "min_warmup_bars": 81
  },
  {
    "id": "gtja191_147",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "regbeta(mean(close,12),sequence(12))",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 24
  },
  {
    "id": "gtja191_148",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume"
    ],
    "decay_horizon": 60,
    "min_warmup_bars": 75
  },
  {
    "id": "gtja191_149",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 60,
    "min_warmup_bars": 253
  },
  {
    "id": "gtja191_150",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "(close+high+low)/3*volume",
    "columns_required": [
      "close",
      "high",
      "low",
      "volume"
    ],
    "decay_horizon": 1,
    "min_warmup_bars": 1
  },
  {
    "id": "gtja191_151",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "sma(close-delay(close,20),20,1)",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_152",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 26,
    "min_warmup_bars": 50
  },
  {
    "id": "gtja191_153",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "(mean(c,3)+mean(c,6)+mean(c,12)+mean(c,24))/4",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 24,
    "min_warmup_bars": 24
  },
  {
    "id": "gtja191_154",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 60,
    "min_warmup_bars": 198
  },
  {
    "id": "gtja191_155",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "sma(v,13,2)-sma(v,27,2)-sma(sma(v,13,2)-sma(v,27,2),10,2)",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 27,
    "min_warmup_bars": 40
  },
  {
    "id": "gtja191_156",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 10
  },
  {
    "id": "gtja191_157",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 5,
    "min_warmup_bars": 12
  },
  {
    "id": "gtja191_158",
    "nickname": null,
    "theme": [
      "volatility"
    ],
    "formula_latex": "((h-sma(c,15,2))-(l-sma(c,15,2)))/c",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 15,
    "min_warmup_bars": 16
  },
  {
    "id": "gtja191_159",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume"
    ],
    "decay_horizon": 24,
    "min_warmup_bars": 25
  },
  {
    "id": "gtja191_160",
    "nickname": null,
    "theme": [
      "volatility"
    ],
    "formula_latex": "sma((c<=delay(c,1)?std(c,20):0),20,1)",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 22
  },
  {
    "id": "gtja191_161",
    "nickname": null,
    "theme": [
      "volatility"
    ],
    "formula_latex": "mean(true_range,12)",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 13
  },
  {
    "id": "gtja191_162",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 24
  },
  {
    "id": "gtja191_163",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "rank(((-1*ret)*mean(v,20))*vwap*(high-close))",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_164",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 13,
    "min_warmup_bars": 20
  },
  {
    "id": "gtja191_165",
    "nickname": null,
    "theme": [
      "volatility"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 48,
    "min_warmup_bars": 142
  },
  {
    "id": "gtja191_166",
    "nickname": null,
    "theme": [
      "volatility"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 40
  },
  {
    "id": "gtja191_167",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "sum(max(0,c-delay(c,1)),12)",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 13
  },
  {
    "id": "gtja191_168",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "-1*volume/mean(volume,20)",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 20
  },
  {
    "id": "gtja191_169",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 26,
    "min_warmup_bars": 50
  },
  {
    "id": "gtja191_170",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_171",
    "nickname": null,
    "theme": [
      "microstructure"
    ],
    "formula_latex": "-1*((l-c)*(o^5))/((c-h)*(c^5))",
    "columns_required": [
      "open",
      "high",
      "low",
      "close"
    ],
    "decay_horizon": 1,
    "min_warmup_bars": 1
  },
  {
    "id": "gtja191_172",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 14,
    "min_warmup_bars": 20
  },
  {
    "id": "gtja191_173",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "3*sma(c,13,2)-2*sma(sma(c,13,2),13,2)+sma(sma(sma(log(c),13,2),13,2),13,2)",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 13,
    "min_warmup_bars": 40
  },
  {
    "id": "gtja191_174",
    "nickname": null,
    "theme": [
      "volatility"
    ],
    "formula_latex": "sma((c>delay(c,1)?std(c,20):0),20,1)",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 22
  },
  {
    "id": "gtja191_175",
    "nickname": null,
    "theme": [
      "volatility"
    ],
    "formula_latex": "mean(true_range,6)",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 6,
    "min_warmup_bars": 7
  },
  {
    "id": "gtja191_176",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume"
    ],
    "decay_horizon": 12,
    "min_warmup_bars": 18
  },
  {
    "id": "gtja191_177",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "((20-highday(h,20))/20)*100",
    "columns_required": [
      "close",
      "high"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 20
  },
  {
    "id": "gtja191_178",
    "nickname": null,
    "theme": [
      "momentum",
      "volume"
    ],
    "formula_latex": "(c-delay(c,1))/delay(c,1)*v",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 1,
    "min_warmup_bars": 2
  },
  {
    "id": "gtja191_179",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "rank(corr(vwap,v,4))*rank(corr(rank(low),rank(mean(v,50)),12))",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume",
      "amount"
    ],
    "decay_horizon": 50,
    "min_warmup_bars": 62
  },
  {
    "id": "gtja191_180",
    "nickname": null,
    "theme": [
      "volume",
      "reversal"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "close",
      "volume"
    ],
    "decay_horizon": 60,
    "min_warmup_bars": 67
  },
  {
    "id": "gtja191_181",
    "nickname": null,
    "theme": [
      "volatility"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 40
  },
  {
    "id": "gtja191_182",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_183",
    "nickname": null,
    "theme": [
      "volatility"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 24,
    "min_warmup_bars": 70
  },
  {
    "id": "gtja191_184",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "close"
    ],
    "decay_horizon": 60,
    "min_warmup_bars": 202
  },
  {
    "id": "gtja191_185",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "rank(-1*(1-open/close)^2)",
    "columns_required": [
      "open",
      "close"
    ],
    "decay_horizon": 1,
    "min_warmup_bars": 1
  },
  {
    "id": "gtja191_186",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "see body (alpha172 averaged with its 6-day lag)",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 14,
    "min_warmup_bars": 27
  },
  {
    "id": "gtja191_187",
    "nickname": null,
    "theme": [
      "reversal"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 21
  },
  {
    "id": "gtja191_188",
    "nickname": null,
    "theme": [
      "volatility"
    ],
    "formula_latex": "(h-l-sma(h-l,11,2))/sma(h-l,11,2)*100",
    "columns_required": [
      "close",
      "high",
      "low"
    ],
    "decay_horizon": 11,
    "min_warmup_bars": 13
  },
  {
    "id": "gtja191_189",
    "nickname": null,
    "theme": [
      "volatility"
    ],
    "formula_latex": "mean(abs(c-mean(c,6)),6)",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 6,
    "min_warmup_bars": 12
  },
  {
    "id": "gtja191_190",
    "nickname": null,
    "theme": [
      "momentum"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "close"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 39
  },
  {
    "id": "gtja191_191",
    "nickname": null,
    "theme": [
      "volume"
    ],
    "formula_latex": "see body",
    "columns_required": [
      "open",
      "high",
      "low",
      "close",
      "volume"
    ],
    "decay_horizon": 20,
    "min_warmup_bars": 25
  }
]
