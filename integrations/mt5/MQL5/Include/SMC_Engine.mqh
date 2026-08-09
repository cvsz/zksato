//+------------------------------------------------------------------+
//|                                                   SMC_Engine.mqh |
//|                    Deterministic SMC analysis / signal engine    |
//+------------------------------------------------------------------+
#property strict

enum ENUM_MARKET_TREND
  {
   TREND_BULLISH = 0,
   TREND_BEARISH = 1,
   TREND_NEUTRAL = 2
  };

enum ENUM_SMC_DIRECTION
  {
   SMC_SIGNAL_NONE = 0,
   SMC_SIGNAL_BUY  = 1,
   SMC_SIGNAL_SELL = 2
  };

struct SMCZone
  {
   bool      valid;
   double    low;
   double    high;
   datetime  origin_time;
  };

struct SMCSignal
  {
   ENUM_MARKET_TREND  trend;
   ENUM_SMC_DIRECTION direction;
   bool               bullish_bos;
   bool               bearish_bos;
   bool               bullish_choch;
   bool               bearish_choch;
   bool               engulfing;
   bool               rejection;
   bool               in_zone;
   double             score;
   SMCZone            zone;
  };

class CSMC_Engine
  {
private:
   string          m_symbol;
   ENUM_TIMEFRAMES m_timeframe;

   bool LoadClosedRates(const int count,MqlRates &rates[])
     {
      if(count < 5)
         return false;

      ArraySetAsSeries(rates,true);
      ResetLastError();
      const int copied=CopyRates(m_symbol,m_timeframe,1,count,rates);
      return(copied >= count);
     }

   bool IsSwingHigh(MqlRates &rates[],const int index,const int span)
     {
      const int total=ArraySize(rates);
      if(index < span || index+span >= total)
         return false;

      const double value=rates[index].high;
      for(int offset=1;offset<=span;offset++)
        {
         if(value <= rates[index-offset].high || value <= rates[index+offset].high)
            return false;
        }
      return true;
     }

   bool IsSwingLow(MqlRates &rates[],const int index,const int span)
     {
      const int total=ArraySize(rates);
      if(index < span || index+span >= total)
         return false;

      const double value=rates[index].low;
      for(int offset=1;offset<=span;offset++)
        {
         if(value >= rates[index-offset].low || value >= rates[index+offset].low)
            return false;
        }
      return true;
     }

   bool FindTwoSwingHighs(MqlRates &rates[],const int span,double &recent,double &older)
     {
      int found=0;
      const int total=ArraySize(rates);
      for(int i=span;i<total-span;i++)
        {
         if(!IsSwingHigh(rates,i,span))
            continue;
         if(found == 0)
            recent=rates[i].high;
         else
           {
            older=rates[i].high;
            return true;
           }
         found++;
        }
      return false;
     }

   bool FindTwoSwingLows(MqlRates &rates[],const int span,double &recent,double &older)
     {
      int found=0;
      const int total=ArraySize(rates);
      for(int i=span;i<total-span;i++)
        {
         if(!IsSwingLow(rates,i,span))
            continue;
         if(found == 0)
            recent=rates[i].low;
         else
           {
            older=rates[i].low;
            return true;
           }
         found++;
        }
      return false;
     }

   bool FindLatestSwingLevels(MqlRates &rates[],const int span,double &swingHigh,double &swingLow)
     {
      bool highFound=false;
      bool lowFound=false;
      const int total=ArraySize(rates);

      for(int i=span;i<total-span && (!highFound || !lowFound);i++)
        {
         if(!highFound && IsSwingHigh(rates,i,span))
           {
            swingHigh=rates[i].high;
            highFound=true;
           }
         if(!lowFound && IsSwingLow(rates,i,span))
           {
            swingLow=rates[i].low;
            lowFound=true;
           }
        }
      return(highFound && lowFound);
     }

   bool FindDemandZone(MqlRates &rates[],const int maxBars,SMCZone &zone)
     {
      const int total=MathMin(ArraySize(rates),maxBars);
      for(int i=1;i<total;i++)
        {
         if(rates[i].close >= rates[i].open)
            continue;
         zone.valid=true;
         zone.low=rates[i].low;
         zone.high=MathMax(rates[i].open,rates[i].close);
         zone.origin_time=rates[i].time;
         return true;
        }
      return false;
     }

   bool FindSupplyZone(MqlRates &rates[],const int maxBars,SMCZone &zone)
     {
      const int total=MathMin(ArraySize(rates),maxBars);
      for(int i=1;i<total;i++)
        {
         if(rates[i].close <= rates[i].open)
            continue;
         zone.valid=true;
         zone.low=MathMin(rates[i].open,rates[i].close);
         zone.high=rates[i].high;
         zone.origin_time=rates[i].time;
         return true;
        }
      return false;
     }

   bool PriceInZone(const double price,const SMCZone &zone)
     {
      if(!zone.valid)
         return false;
      return(price >= zone.low && price <= zone.high);
     }

public:
   CSMC_Engine(string symbol,ENUM_TIMEFRAMES timeframe)
     {
      m_symbol=symbol;
      m_timeframe=timeframe;
     }

   ENUM_MARKET_TREND GetStructureTrend(const int lookback=60,const int swingSpan=2)
     {
      MqlRates rates[];
      const int required=MathMax(lookback,(swingSpan*2)+8);
      if(!LoadClosedRates(required,rates))
         return TREND_NEUTRAL;

      double recentHigh=0.0,olderHigh=0.0,recentLow=0.0,olderLow=0.0;
      if(!FindTwoSwingHighs(rates,swingSpan,recentHigh,olderHigh) ||
         !FindTwoSwingLows(rates,swingSpan,recentLow,olderLow))
         return TREND_NEUTRAL;

      if(recentHigh > olderHigh && recentLow > olderLow)
         return TREND_BULLISH;
      if(recentHigh < olderHigh && recentLow < olderLow)
         return TREND_BEARISH;
      return TREND_NEUTRAL;
     }

   bool GetBreakState(bool &bullishBreak,bool &bearishBreak,const int lookback=60,const int swingSpan=2)
     {
      bullishBreak=false;
      bearishBreak=false;

      MqlRates rates[];
      const int required=MathMax(lookback,(swingSpan*2)+8);
      if(!LoadClosedRates(required,rates))
         return false;

      double swingHigh=0.0,swingLow=0.0;
      if(!FindLatestSwingLevels(rates,swingSpan,swingHigh,swingLow))
         return false;

      bullishBreak=(rates[0].close > swingHigh);
      bearishBreak=(rates[0].close < swingLow);
      return true;
     }

   bool IsBullishEngulfing()
     {
      MqlRates rates[];
      if(!LoadClosedRates(3,rates))
         return false;

      const bool previousBearish=(rates[1].close < rates[1].open);
      const bool currentBullish=(rates[0].close > rates[0].open);
      const bool bodyEngulf=(rates[0].open <= rates[1].close && rates[0].close >= rates[1].open);
      const bool closesStrong=(rates[0].close > rates[1].high);
      return(previousBearish && currentBullish && bodyEngulf && closesStrong);
     }

   bool IsBearishEngulfing()
     {
      MqlRates rates[];
      if(!LoadClosedRates(3,rates))
         return false;

      const bool previousBullish=(rates[1].close > rates[1].open);
      const bool currentBearish=(rates[0].close < rates[0].open);
      const bool bodyEngulf=(rates[0].open >= rates[1].close && rates[0].close <= rates[1].open);
      const bool closesStrong=(rates[0].close < rates[1].low);
      return(previousBullish && currentBearish && bodyEngulf && closesStrong);
     }

   bool IsBullishRejection(const double minWickToBody=1.5)
     {
      MqlRates rates[];
      if(!LoadClosedRates(2,rates))
         return false;

      const double body=MathMax(MathAbs(rates[0].close-rates[0].open),_Point);
      const double lowerWick=MathMin(rates[0].open,rates[0].close)-rates[0].low;
      const double range=MathMax(rates[0].high-rates[0].low,_Point);
      const bool closesUpper=(rates[0].close >= rates[0].low+(range*0.60));
      return(lowerWick >= body*minWickToBody && closesUpper);
     }

   bool IsBearishRejection(const double minWickToBody=1.5)
     {
      MqlRates rates[];
      if(!LoadClosedRates(2,rates))
         return false;

      const double body=MathMax(MathAbs(rates[0].close-rates[0].open),_Point);
      const double upperWick=rates[0].high-MathMax(rates[0].open,rates[0].close);
      const double range=MathMax(rates[0].high-rates[0].low,_Point);
      const bool closesLower=(rates[0].close <= rates[0].low+(range*0.40));
      return(upperWick >= body*minWickToBody && closesLower);
     }

   bool EvaluateSignal(SMCSignal &signal,
                       const int lookback=60,
                       const int swingSpan=2,
                       const int zoneLookback=12,
                       const bool requireZoneRetest=false,
                       const double rejectionRatio=1.5)
     {
      signal.trend=TREND_NEUTRAL;
      signal.direction=SMC_SIGNAL_NONE;
      signal.bullish_bos=false;
      signal.bearish_bos=false;
      signal.bullish_choch=false;
      signal.bearish_choch=false;
      signal.engulfing=false;
      signal.rejection=false;
      signal.in_zone=false;
      signal.score=0.0;
      signal.zone.valid=false;
      signal.zone.low=0.0;
      signal.zone.high=0.0;
      signal.zone.origin_time=0;

      MqlRates rates[];
      const int required=MathMax(MathMax(lookback,zoneLookback+3),(swingSpan*2)+8);
      if(!LoadClosedRates(required,rates))
         return false;

      signal.trend=GetStructureTrend(lookback,swingSpan);

      bool bullishBreak=false,bearishBreak=false;
      if(!GetBreakState(bullishBreak,bearishBreak,lookback,swingSpan))
         return false;

      signal.bullish_bos=(bullishBreak && signal.trend == TREND_BULLISH);
      signal.bearish_bos=(bearishBreak && signal.trend == TREND_BEARISH);
      signal.bullish_choch=(bullishBreak && signal.trend == TREND_BEARISH);
      signal.bearish_choch=(bearishBreak && signal.trend == TREND_BULLISH);

      const bool bullishEngulf=IsBullishEngulfing();
      const bool bearishEngulf=IsBearishEngulfing();
      const bool bullishReject=IsBullishRejection(rejectionRatio);
      const bool bearishReject=IsBearishRejection(rejectionRatio);

      const bool bullishContext=(signal.trend == TREND_BULLISH || bullishBreak);
      const bool bearishContext=(signal.trend == TREND_BEARISH || bearishBreak);
      const double closePrice=rates[0].close;

      SMCZone demand;
      demand.valid=false;
      SMCZone supply;
      supply.valid=false;
      FindDemandZone(rates,zoneLookback,demand);
      FindSupplyZone(rates,zoneLookback,supply);

      double buyScore=0.0;
      if(signal.trend == TREND_BULLISH) buyScore+=1.0;
      if(bullishBreak)                 buyScore+=1.0;
      if(bullishEngulf)                buyScore+=1.0;
      if(bullishReject)                buyScore+=0.5;
      if(PriceInZone(closePrice,demand)) buyScore+=0.5;

      double sellScore=0.0;
      if(signal.trend == TREND_BEARISH) sellScore+=1.0;
      if(bearishBreak)                  sellScore+=1.0;
      if(bearishEngulf)                 sellScore+=1.0;
      if(bearishReject)                 sellScore+=0.5;
      if(PriceInZone(closePrice,supply)) sellScore+=0.5;

      const bool buyConfirmed=(bullishEngulf || bullishReject);
      const bool sellConfirmed=(bearishEngulf || bearishReject);
      const bool buyZoneOk=(!requireZoneRetest || PriceInZone(closePrice,demand));
      const bool sellZoneOk=(!requireZoneRetest || PriceInZone(closePrice,supply));

      if(bullishContext && buyConfirmed && buyZoneOk && buyScore > sellScore)
        {
         signal.direction=SMC_SIGNAL_BUY;
         signal.engulfing=bullishEngulf;
         signal.rejection=bullishReject;
         signal.zone=demand;
         signal.in_zone=PriceInZone(closePrice,demand);
         signal.score=buyScore;
        }
      else if(bearishContext && sellConfirmed && sellZoneOk && sellScore > buyScore)
        {
         signal.direction=SMC_SIGNAL_SELL;
         signal.engulfing=bearishEngulf;
         signal.rejection=bearishReject;
         signal.zone=supply;
         signal.in_zone=PriceInZone(closePrice,supply);
         signal.score=sellScore;
        }

      return true;
     }
  };
