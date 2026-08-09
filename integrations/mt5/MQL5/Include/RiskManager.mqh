//+------------------------------------------------------------------+
//|                                                  RiskManager.mqh |
//|                    Guarded risk / basket / layering management   |
//+------------------------------------------------------------------+
#property strict

#include <Trade\Trade.mqh>

class CRiskManager
  {
private:
   CTrade m_trade;
   ulong  m_magic;
   string m_symbol;
   int    m_deviationPoints;

   int VolumeDigits(const double step)
     {
      int digits=0;
      double scaled=step;
      while(digits < 8 && MathAbs(scaled-MathRound(scaled)) > 1e-8)
        {
         scaled*=10.0;
         digits++;
        }
      return digits;
     }

   double NormalizePrice(const double price)
     {
      const int digits=(int)SymbolInfoInteger(m_symbol,SYMBOL_DIGITS);
      return NormalizeDouble(price,digits);
     }

   double MinimumStopDistance()
     {
      const double point=SymbolInfoDouble(m_symbol,SYMBOL_POINT);
      const long stopsLevel=SymbolInfoInteger(m_symbol,SYMBOL_TRADE_STOPS_LEVEL);
      return MathMax(0.0,(double)stopsLevel*point);
     }

   bool IsManagedSelectedPosition()
     {
      return(PositionGetString(POSITION_SYMBOL) == m_symbol &&
             (ulong)PositionGetInteger(POSITION_MAGIC) == m_magic);
     }

public:
   CRiskManager(ulong magic,string symbol,int deviationPoints=30)
     {
      m_magic=magic;
      m_symbol=symbol;
      m_deviationPoints=MathMax(0,deviationPoints);
      m_trade.SetExpertMagicNumber(m_magic);
      m_trade.SetDeviationInPoints(m_deviationPoints);
      m_trade.SetTypeFillingBySymbol(m_symbol);
      m_trade.SetAsyncMode(false);
     }

   bool IsRealAccount()
     {
      return((ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL);
     }

   bool IsHedgingAccount()
     {
      return((ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE) == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING);
     }

   bool TradingAvailable(string &reason)
     {
      reason="";
      if(!TerminalInfoInteger(TERMINAL_CONNECTED))
        {
         reason="terminal is not connected";
         return false;
        }
      if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
        {
         reason="terminal Algo Trading is disabled";
         return false;
        }
      if(!MQLInfoInteger(MQL_TRADE_ALLOWED))
        {
         reason="EA trading permission is disabled";
         return false;
        }
      if(!AccountInfoInteger(ACCOUNT_TRADE_ALLOWED) || !AccountInfoInteger(ACCOUNT_TRADE_EXPERT))
        {
         reason="account does not allow expert trading";
         return false;
        }
      return true;
     }

   double GetPipSize()
     {
      const int digits=(int)SymbolInfoInteger(m_symbol,SYMBOL_DIGITS);
      const double point=SymbolInfoDouble(m_symbol,SYMBOL_POINT);
      if(digits == 3 || digits == 5)
         return(point*10.0);
      return point;
     }

   double GetSpreadPips()
     {
      const double bid=SymbolInfoDouble(m_symbol,SYMBOL_BID);
      const double ask=SymbolInfoDouble(m_symbol,SYMBOL_ASK);
      const double pip=GetPipSize();
      if(bid <= 0.0 || ask <= 0.0 || pip <= 0.0)
         return DBL_MAX;
      return((ask-bid)/pip);
     }

   bool NormalizeVolume(const double requested,double &normalized,string &reason)
     {
      reason="";
      const double minVolume=SymbolInfoDouble(m_symbol,SYMBOL_VOLUME_MIN);
      const double maxVolume=SymbolInfoDouble(m_symbol,SYMBOL_VOLUME_MAX);
      const double step=SymbolInfoDouble(m_symbol,SYMBOL_VOLUME_STEP);
      if(minVolume <= 0.0 || maxVolume <= 0.0 || step <= 0.0)
        {
         reason="symbol volume constraints unavailable";
         return false;
        }
      if(requested < minVolume-1e-12 || requested > maxVolume+1e-12)
        {
         reason="requested lot is outside broker min/max volume";
         return false;
        }

      const double units=MathRound(requested/step);
      normalized=NormalizeDouble(units*step,VolumeDigits(step));
      if(normalized < minVolume-1e-12 || normalized > maxVolume+1e-12 ||
         MathAbs(normalized-requested) > MathMax(step*0.001,1e-8))
        {
         reason="requested lot does not align with broker volume step";
         return false;
        }
      return true;
     }

   int CountPositions(const ENUM_POSITION_TYPE posType)
     {
      int count=0;
      for(int i=PositionsTotal()-1;i>=0;i--)
        {
         const ulong ticket=PositionGetTicket(i);
         if(ticket == 0 || !IsManagedSelectedPosition())
            continue;
         if((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) == posType)
            count++;
        }
      return count;
     }

   double GetPositionVolume(const ENUM_POSITION_TYPE posType)
     {
      double total=0.0;
      for(int i=PositionsTotal()-1;i>=0;i--)
        {
         const ulong ticket=PositionGetTicket(i);
         if(ticket == 0 || !IsManagedSelectedPosition())
            continue;
         if((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) == posType)
            total+=PositionGetDouble(POSITION_VOLUME);
        }
      return total;
     }

   double GetTotalManagedVolume()
     {
      return(GetPositionVolume(POSITION_TYPE_BUY)+GetPositionVolume(POSITION_TYPE_SELL));
     }

   int CountLayers(const ENUM_POSITION_TYPE posType,const double layerLot)
     {
      if(layerLot <= 0.0)
         return 0;
      const double volume=GetPositionVolume(posType);
      if(volume <= 0.0)
         return 0;
      return(int)MathCeil((volume/layerLot)-1e-8);
     }

   double GetBasketProfitUSD()
     {
      double total=0.0;
      for(int i=PositionsTotal()-1;i>=0;i--)
        {
         const ulong ticket=PositionGetTicket(i);
         if(ticket == 0 || !IsManagedSelectedPosition())
            continue;
         total+=PositionGetDouble(POSITION_PROFIT)+PositionGetDouble(POSITION_SWAP);
        }
      return total;
     }

   bool CloseAll()
     {
      bool allClosed=true;
      for(int i=PositionsTotal()-1;i>=0;i--)
        {
         const ulong ticket=PositionGetTicket(i);
         if(ticket == 0 || !IsManagedSelectedPosition())
            continue;
         if(!m_trade.PositionClose(ticket,m_deviationPoints))
           {
            allClosed=false;
            Print("Close failed ticket=",ticket,
                  " retcode=",m_trade.ResultRetcode(),
                  " ",m_trade.ResultRetcodeDescription());
           }
        }
      return allClosed;
     }

   double GetLastEntryDealPrice(const ENUM_POSITION_TYPE posType)
     {
      const datetime now=TimeCurrent();
      if(!HistorySelect(now-(86400*30),now))
         return 0.0;

      datetime latest=0;
      double lastPrice=0.0;
      const int deals=HistoryDealsTotal();
      for(int i=0;i<deals;i++)
        {
         const ulong ticket=HistoryDealGetTicket(i);
         if(ticket == 0)
            continue;
         if(HistoryDealGetString(ticket,DEAL_SYMBOL) != m_symbol)
            continue;
         if((ulong)HistoryDealGetInteger(ticket,DEAL_MAGIC) != m_magic)
            continue;

         const ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(ticket,DEAL_ENTRY);
         if(entry != DEAL_ENTRY_IN && entry != DEAL_ENTRY_INOUT)
            continue;

         const ENUM_DEAL_TYPE dealType=(ENUM_DEAL_TYPE)HistoryDealGetInteger(ticket,DEAL_TYPE);
         if(posType == POSITION_TYPE_BUY && dealType != DEAL_TYPE_BUY)
            continue;
         if(posType == POSITION_TYPE_SELL && dealType != DEAL_TYPE_SELL)
            continue;

         const datetime dealTime=(datetime)HistoryDealGetInteger(ticket,DEAL_TIME);
         if(dealTime >= latest)
           {
            latest=dealTime;
            lastPrice=HistoryDealGetDouble(ticket,DEAL_PRICE);
           }
        }
      return lastPrice;
     }

   bool CanOpen(const double lot,const double maxTotalLots,const double maxSpreadPips,string &reason)
     {
      reason="";
      string availability="";
      if(!TradingAvailable(availability))
        {
         reason=availability;
         return false;
        }

      double normalized=0.0;
      if(!NormalizeVolume(lot,normalized,reason))
         return false;

      if(maxTotalLots > 0.0 && GetTotalManagedVolume()+normalized > maxTotalLots+1e-10)
        {
         reason="maximum total managed lots would be exceeded";
         return false;
        }

      const double spread=GetSpreadPips();
      if(maxSpreadPips > 0.0 && spread > maxSpreadPips)
        {
         reason="spread exceeds configured maximum";
         return false;
        }
      return true;
     }

   bool OpenBuy(const double requestedLot,
                const double emergencySLPips,
                const double maxTotalLots,
                const double maxSpreadPips,
                const string comment,
                string &reason)
     {
      if(!CanOpen(requestedLot,maxTotalLots,maxSpreadPips,reason))
         return false;

      double lot=0.0;
      if(!NormalizeVolume(requestedLot,lot,reason))
         return false;

      const double ask=SymbolInfoDouble(m_symbol,SYMBOL_ASK);
      if(ask <= 0.0)
        {
         reason="invalid ask price";
         return false;
        }

      double sl=0.0;
      if(emergencySLPips > 0.0)
        {
         const double requestedDistance=emergencySLPips*GetPipSize();
         const double distance=MathMax(requestedDistance,MinimumStopDistance());
         sl=NormalizePrice(ask-distance);
        }

      if(!m_trade.Buy(lot,m_symbol,0.0,sl,0.0,comment))
        {
         reason=StringFormat("buy rejected retcode=%I64u %s",
                             m_trade.ResultRetcode(),
                             m_trade.ResultRetcodeDescription());
         return false;
        }
      reason="";
      return true;
     }

   bool OpenSell(const double requestedLot,
                 const double emergencySLPips,
                 const double maxTotalLots,
                 const double maxSpreadPips,
                 const string comment,
                 string &reason)
     {
      if(!CanOpen(requestedLot,maxTotalLots,maxSpreadPips,reason))
         return false;

      double lot=0.0;
      if(!NormalizeVolume(requestedLot,lot,reason))
         return false;

      const double bid=SymbolInfoDouble(m_symbol,SYMBOL_BID);
      if(bid <= 0.0)
        {
         reason="invalid bid price";
         return false;
        }

      double sl=0.0;
      if(emergencySLPips > 0.0)
        {
         const double requestedDistance=emergencySLPips*GetPipSize();
         const double distance=MathMax(requestedDistance,MinimumStopDistance());
         sl=NormalizePrice(bid+distance);
        }

      if(!m_trade.Sell(lot,m_symbol,0.0,sl,0.0,comment))
        {
         reason=StringFormat("sell rejected retcode=%I64u %s",
                             m_trade.ResultRetcode(),
                             m_trade.ResultRetcodeDescription());
         return false;
        }
      reason="";
      return true;
     }

   void ApplyTrailingStop(const double trailingPips)
     {
      if(trailingPips <= 0.0)
         return;

      const double bid=SymbolInfoDouble(m_symbol,SYMBOL_BID);
      const double ask=SymbolInfoDouble(m_symbol,SYMBOL_ASK);
      const double point=SymbolInfoDouble(m_symbol,SYMBOL_POINT);
      if(bid <= 0.0 || ask <= 0.0 || point <= 0.0)
         return;

      const double distance=MathMax(trailingPips*GetPipSize(),MinimumStopDistance());
      const double improvement=MathMax(5.0*point,point);

      for(int i=PositionsTotal()-1;i>=0;i--)
        {
         const ulong ticket=PositionGetTicket(i);
         if(ticket == 0 || !IsManagedSelectedPosition())
            continue;

         const ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
         const double currentSL=PositionGetDouble(POSITION_SL);
         const double currentTP=PositionGetDouble(POSITION_TP);

         if(type == POSITION_TYPE_BUY)
           {
            const double newSL=NormalizePrice(bid-distance);
            if(newSL > 0.0 && (currentSL == 0.0 || newSL > currentSL+improvement))
              {
               if(!m_trade.PositionModify(ticket,newSL,currentTP))
                  Print("Trailing BUY modify failed ticket=",ticket,
                        " retcode=",m_trade.ResultRetcode(),
                        " ",m_trade.ResultRetcodeDescription());
              }
           }
         else if(type == POSITION_TYPE_SELL)
           {
            const double newSL=NormalizePrice(ask+distance);
            if(newSL > 0.0 && (currentSL == 0.0 || newSL < currentSL-improvement))
              {
               if(!m_trade.PositionModify(ticket,newSL,currentTP))
                  Print("Trailing SELL modify failed ticket=",ticket,
                        " retcode=",m_trade.ResultRetcode(),
                        " ",m_trade.ResultRetcodeDescription());
              }
           }
        }
     }
  };
