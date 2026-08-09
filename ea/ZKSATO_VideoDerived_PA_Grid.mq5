#property strict
#property version   "0.10"
#property description "Video-derived PA + bounded stop-grid research EA"
#property description "DEMO/Strategy Tester only. Real-account initialization is blocked."

#include <Trade/Trade.mqh>

CTrade trade;

enum ENUM_ZKSATO_GRID_MODE
  {
   ZKSATO_PA_FILTERED = 0,
   ZKSATO_SYMMETRIC_RESEARCH = 1
  };

input ENUM_ZKSATO_GRID_MODE InpGridMode = ZKSATO_PA_FILTERED;
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_M5;
input ulong  InpMagic = 26080901;
input double InpLots = 0.01;
input double InpGridStepPrice = 0.30;
input int    InpLevelsPerSide = 6;
input int    InpMaxPositions = 12;
input int    InpMaxPendingOrders = 12;
input double InpMaxCycleVolume = 0.12;
input double InpBasketProfitCurrency = 5.00;
input double InpBasketMaxLossCurrency = 10.00;
input int    InpCooldownSeconds = 15;
input int    InpMaxSpreadPoints = 80;
input int    InpLookbackBars = 48;
input int    InpPivotWindow = 2;
input int    InpAtrPeriod = 14;
input double InpBreakoutBufferATR = 0.10;
input double InpRetestToleranceATR = 0.35;
input double InpRejectionWickRatio = 0.50;
input double InpCycleStopATR = 1.00;

int      g_bias = 0;              // +1 long, -1 short, 0 neutral
double   g_zone_level = 0.0;
double   g_last_atr = 0.0;
bool     g_pa_ready = false;
datetime g_last_bar_time = 0;
datetime g_cooldown_until = 0;

int OnInit()
  {
   ENUM_ACCOUNT_TRADE_MODE mode=(ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE);
   if(mode==ACCOUNT_TRADE_MODE_REAL)
     {
      Print("ZKSATO VideoDerived EA refuses real accounts. Use Strategy Tester or demo only.");
      return(INIT_FAILED);
     }

   if(InpLots<=0.0 || InpGridStepPrice<=0.0 || InpLevelsPerSide<1 ||
      InpMaxPositions<1 || InpMaxPendingOrders<1 || InpMaxCycleVolume<InpLots ||
      InpBasketProfitCurrency<=0.0 || InpBasketMaxLossCurrency<=0.0 ||
      InpLookbackBars<12 || InpPivotWindow<1 || InpAtrPeriod<2)
      return(INIT_PARAMETERS_INCORRECT);

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetAsyncMode(false);
   return(INIT_SUCCEEDED);
  }

void OnTick()
  {
   if(TimeCurrent()<g_cooldown_until)
      return;
   if(!SpreadOK())
      return;

   int positions=CountPositions();
   int pending=CountPendingOrders();
   if(positions>0)
     {
      double basket=BasketProfit();
      if(basket>=InpBasketProfitCurrency)
        {
         FlattenCycle("basket-profit");
         return;
        }
      if(basket<=-InpBasketMaxLossCurrency)
        {
         FlattenCycle("basket-loss");
         return;
        }
     }

   if(IsNewBar() && InpGridMode==ZKSATO_PA_FILTERED)
      DetectPriceActionBias();

   positions=CountPositions();
   pending=CountPendingOrders();
   if(positions==0 && pending==0)
     {
      if(InpGridMode==ZKSATO_SYMMETRIC_RESEARCH)
         SeedGrid(0);
      else if(g_pa_ready && g_bias!=0)
         SeedGrid(g_bias);
     }
  }

bool SpreadOK()
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return(false);
   double spread=(tick.ask-tick.bid)/_Point;
   return(spread>=0.0 && spread<=InpMaxSpreadPoints);
  }

bool IsNewBar()
  {
   datetime current=iTime(_Symbol,InpTimeframe,0);
   if(current<=0)
      return(false);
   if(current==g_last_bar_time)
      return(false);
   g_last_bar_time=current;
   return(true);
  }

int CountPositions()
  {
   int count=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagic)
         continue;
      count++;
     }
   return(count);
  }

int CountPendingOrders()
  {
   int count=0;
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0)
         continue;
      if(OrderGetString(ORDER_SYMBOL)!=_Symbol)
         continue;
      if((ulong)OrderGetInteger(ORDER_MAGIC)!=InpMagic)
         continue;
      count++;
     }
   return(count);
  }

double BasketProfit()
  {
   double value=0.0;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagic)
         continue;
      value+=PositionGetDouble(POSITION_PROFIT);
      value+=PositionGetDouble(POSITION_SWAP);
     }
   return(value);
  }

void FlattenCycle(const string reason)
  {
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0)
         continue;
      if(OrderGetString(ORDER_SYMBOL)!=_Symbol || (ulong)OrderGetInteger(ORDER_MAGIC)!=InpMagic)
         continue;
      if(!trade.OrderDelete(ticket))
         PrintFormat("delete pending failed ticket=%I64u retcode=%u",ticket,trade.ResultRetcode());
     }

   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol || (ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagic)
         continue;
      if(!trade.PositionClose(ticket))
         PrintFormat("close position failed ticket=%I64u retcode=%u",ticket,trade.ResultRetcode());
     }

   PrintFormat("cycle flattened: %s",reason);
   g_bias=0;
   g_zone_level=0.0;
   g_last_atr=0.0;
   g_pa_ready=false;
   g_cooldown_until=TimeCurrent()+InpCooldownSeconds;
  }

void SeedGrid(const int directional_bias)
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return;

   int sides=(directional_bias==0 ? 2 : 1);
   int volume_slots=(int)MathFloor((InpMaxCycleVolume+1e-12)/InpLots);
   int hard_slots=MathMin(InpMaxPositions,InpMaxPendingOrders);
   hard_slots=MathMin(hard_slots,volume_slots);
   int levels=MathMin(InpLevelsPerSide,hard_slots/sides);
   if(levels<1)
     {
      Print("grid not seeded: hard caps leave no available level");
      return;
     }

   double anchor=(tick.bid+tick.ask)/2.0;
   if(directional_bias>=0)
      PlaceBuyStops(anchor,levels);
   if(directional_bias<=0)
      PlaceSellStops(anchor,levels);
  }

void PlaceBuyStops(const double anchor,const int levels)
  {
   double stop_loss=0.0;
   if(InpGridMode==ZKSATO_PA_FILTERED && g_zone_level>0.0 && g_last_atr>0.0)
      stop_loss=NormalizePrice(g_zone_level-(g_last_atr*InpCycleStopATR));

   for(int level=1;level<=levels;level++)
     {
      if(CountPendingOrders()>=InpMaxPendingOrders)
         return;
      double price=NormalizePrice(anchor+(InpGridStepPrice*level));
      string comment=StringFormat("ZK-VPA-B-%d",level);
      if(!trade.BuyStop(InpLots,price,_Symbol,stop_loss,0.0,ORDER_TIME_GTC,0,comment))
         PrintFormat("BuyStop failed level=%d price=%.*f retcode=%u",level,_Digits,price,trade.ResultRetcode());
     }
  }

void PlaceSellStops(const double anchor,const int levels)
  {
   double stop_loss=0.0;
   if(InpGridMode==ZKSATO_PA_FILTERED && g_zone_level>0.0 && g_last_atr>0.0)
      stop_loss=NormalizePrice(g_zone_level+(g_last_atr*InpCycleStopATR));

   for(int level=1;level<=levels;level++)
     {
      if(CountPendingOrders()>=InpMaxPendingOrders)
         return;
      double price=NormalizePrice(anchor-(InpGridStepPrice*level));
      string comment=StringFormat("ZK-VPA-S-%d",level);
      if(!trade.SellStop(InpLots,price,_Symbol,stop_loss,0.0,ORDER_TIME_GTC,0,comment))
         PrintFormat("SellStop failed level=%d price=%.*f retcode=%u",level,_Digits,price,trade.ResultRetcode());
     }
  }

double NormalizePrice(const double value)
  {
   double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick_size<=0.0)
      tick_size=_Point;
   double ticks=MathRound(value/tick_size);
   return(NormalizeDouble(ticks*tick_size,_Digits));
  }

void DetectPriceActionBias()
  {
   MqlRates rates[];
   ArraySetAsSeries(rates,false);
   int copied=CopyRates(_Symbol,InpTimeframe,1,InpLookbackBars,rates);
   int minimum=MathMax(InpAtrPeriod+2,(InpPivotWindow*2)+5);
   if(copied<minimum)
     {
      g_pa_ready=false;
      g_bias=0;
      return;
     }

   double atr_value=AverageTrueRange(rates,copied,InpAtrPeriod);
   if(atr_value<=0.0)
     {
      g_pa_ready=false;
      g_bias=0;
      return;
     }

   double breakout_buffer=atr_value*InpBreakoutBufferATR;
   double retest_tolerance=atr_value*InpRetestToleranceATR;
   int latest_index=-1;
   int latest_bias=0;
   double latest_level=0.0;

   for(int pivot=InpPivotWindow;pivot<copied-InpPivotWindow;pivot++)
     {
      if(IsPivotHigh(rates,copied,pivot,InpPivotWindow))
        {
         double level=rates[pivot].high;
         bool breakout_found=false;
         for(int breakout=pivot+1;breakout<copied-1;breakout++)
           {
            if(rates[breakout].close<=level+breakout_buffer)
               continue;
            breakout_found=true;
            for(int retest=breakout+1;retest<copied;retest++)
              {
               bool touched=rates[retest].low<=level+retest_tolerance;
               bool held=rates[retest].close>=level-retest_tolerance;
               if(touched && held && BullishPA(rates,retest,InpRejectionWickRatio))
                 {
                  if(retest>latest_index)
                    {
                     latest_index=retest;
                     latest_bias=1;
                     latest_level=level;
                    }
                  break;
                 }
              }
            if(breakout_found)
               break;
           }
        }

      if(IsPivotLow(rates,copied,pivot,InpPivotWindow))
        {
         double level=rates[pivot].low;
         bool breakout_found=false;
         for(int breakout=pivot+1;breakout<copied-1;breakout++)
           {
            if(rates[breakout].close>=level-breakout_buffer)
               continue;
            breakout_found=true;
            for(int retest=breakout+1;retest<copied;retest++)
              {
               bool touched=rates[retest].high>=level-retest_tolerance;
               bool held=rates[retest].close<=level+retest_tolerance;
               if(touched && held && BearishPA(rates,retest,InpRejectionWickRatio))
                 {
                  if(retest>latest_index)
                    {
                     latest_index=retest;
                     latest_bias=-1;
                     latest_level=level;
                    }
                  break;
                 }
              }
            if(breakout_found)
               break;
           }
        }
     }

   if(latest_bias==0)
     {
      int last=copied-1;
      for(int pivot=copied-InpPivotWindow-1;pivot>=InpPivotWindow;pivot--)
        {
         if(IsPivotLow(rates,copied,pivot,InpPivotWindow))
           {
            double level=rates[pivot].low;
            if(rates[last].low<=level+retest_tolerance && rates[last].close>=level &&
               BullishPA(rates,last,InpRejectionWickRatio))
              {
               latest_bias=1;
               latest_level=level;
               break;
              }
           }
         if(IsPivotHigh(rates,copied,pivot,InpPivotWindow))
           {
            double level=rates[pivot].high;
            if(rates[last].high>=level-retest_tolerance && rates[last].close<=level &&
               BearishPA(rates,last,InpRejectionWickRatio))
              {
               latest_bias=-1;
               latest_level=level;
               break;
              }
           }
        }
     }

   g_last_atr=atr_value;
   g_bias=latest_bias;
   g_zone_level=latest_level;
   g_pa_ready=(latest_bias!=0 && latest_level>0.0);
  }

double AverageTrueRange(const MqlRates &rates[],const int count,const int period)
  {
   if(count<=period || period<1)
      return(0.0);
   int start=MathMax(1,count-period);
   double total=0.0;
   int samples=0;
   for(int i=start;i<count;i++)
     {
      double range1=rates[i].high-rates[i].low;
      double range2=MathAbs(rates[i].high-rates[i-1].close);
      double range3=MathAbs(rates[i].low-rates[i-1].close);
      total+=MathMax(range1,MathMax(range2,range3));
      samples++;
     }
   return(samples>0 ? total/samples : 0.0);
  }

bool IsPivotHigh(const MqlRates &rates[],const int count,const int index,const int window)
  {
   if(index-window<0 || index+window>=count)
      return(false);
   double value=rates[index].high;
   for(int i=1;i<=window;i++)
     {
      if(value<rates[index-i].high || value<=rates[index+i].high)
         return(false);
     }
   return(true);
  }

bool IsPivotLow(const MqlRates &rates[],const int count,const int index,const int window)
  {
   if(index-window<0 || index+window>=count)
      return(false);
   double value=rates[index].low;
   for(int i=1;i<=window;i++)
     {
      if(value>rates[index-i].low || value>=rates[index+i].low)
         return(false);
     }
   return(true);
  }

bool BullishPA(const MqlRates &rates[],const int index,const double wick_ratio)
  {
   if(index<0)
      return(false);
   double body=MathMax(MathAbs(rates[index].close-rates[index].open),_Point);
   double lower_wick=MathMin(rates[index].open,rates[index].close)-rates[index].low;
   bool rejection=(rates[index].close>=rates[index].open && lower_wick>=body*wick_ratio);
   bool engulfing=false;
   if(index>0)
     {
      engulfing=(rates[index-1].close<rates[index-1].open &&
                 rates[index].close>rates[index].open &&
                 rates[index].close>=rates[index-1].open &&
                 rates[index].open<=rates[index-1].close);
     }
   return(rejection || engulfing);
  }

bool BearishPA(const MqlRates &rates[],const int index,const double wick_ratio)
  {
   if(index<0)
      return(false);
   double body=MathMax(MathAbs(rates[index].close-rates[index].open),_Point);
   double upper_wick=rates[index].high-MathMax(rates[index].open,rates[index].close);
   bool rejection=(rates[index].close<=rates[index].open && upper_wick>=body*wick_ratio);
   bool engulfing=false;
   if(index>0)
     {
      engulfing=(rates[index-1].close>rates[index-1].open &&
                 rates[index].close<rates[index].open &&
                 rates[index].open>=rates[index-1].close &&
                 rates[index].close<=rates[index-1].open);
     }
   return(rejection || engulfing);
  }
