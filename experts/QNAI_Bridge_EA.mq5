//+------------------------------------------------------------------+
//| Quant Nanggroe AI — MT5 EA Bridge (Copy-Trade dari terminal)     |
//|                                                                    |
//| Exness / Valutrades / broker retail TIDAK punya API publik.       |
//| Solusi: jalankan QNAI Python di PC yang sama dengan MT5 terminal, |
//| EA ini kirim sinyal order lewat named-pipe / file ke QNAI, lalu   |
//| QNAI eksekusi via MT5Broker langsung di terminal yang sama.       |
//|                                                                    |
//| Ini EA minimal: pasang di chart, setiap order baru di terminal    |
//| ditulis ke C:\qnai\signals\<ticket>.json. QNAI watchdog baca,     |
//| forward ke /api/brokers/{akun}/order.                             |
//+------------------------------------------------------------------+
#property strict
#include <Files\FileAccess.mqh>

string SignalDir = "C:\\qnai\\signals\\";

void OnTradeTransaction(const MqlTradeTransaction& trans, const MqlTradeRequest& request, const MqlTradeResult& result)
{
   if(trans.type == TRADE_TRANSACTION_ORDER_ADD && result.retcode == TRADE_RETCODE_DONE)
   {
      string fname = SignalDir + IntegerToString(trans.order) + ".json";
      int f = FileOpen(fname, FILE_WRITE | FILE_ANSI);
      if(f != INVALID_HANDLE)
      {
         FileWrite(f, "{\"ticket\":", trans.order, ",\"symbol\":\"", trans.symbol, "\",\"type\":", trans.type, ",\"volume\":", trans.volume, ",\"price\":", trans.price, "}");
         FileClose(f);
      }
   }
}

int OnInit() { FileMail("",""); return INIT_SUCCEEDED; }
void OnDeinit(const int reason) {}
void OnTick() {}
//+------------------------------------------------------------------+
