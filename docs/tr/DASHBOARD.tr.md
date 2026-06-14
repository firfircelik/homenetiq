# HomeNetIQ Dashboard (Türkçe)

> 🇬🇧 English: [docs/DASHBOARD.md](../DASHBOARD.md)

Streamlit tabanlı yerel dashboard. Backend API'sine bağlanır, metrikleri
insan-okunabilir grafik/tablo/açıklamalara çevirir.

## Sayfa yapısı (8 sayfa)

| Sayfa | İçerik |
|---|---|
| Overview | Overall health, kalite skoru, son ölçüm, cihaz durumları, top issues, top recommendations |
| Devices | Tüm cihazlar, son kalite/score, status (active/stale/offline) |
| Wi-Fi Metrics | RSSI/SNR/Tx rate zaman serisi, band dağılımı, son bağlantı bilgisi |
| Network Metrics | Gateway/AP/Internet/DNS latency, packet loss, jitter, kısa yorum |
| Issues & Root Cause | Son issue'lar (kod + açıklama), root cause dağılımı |
| Recommendations | Tekrarsız, öncelikli öneri listesi |
| Raw Metrics | Tablo + JSON debug görünümü |
| About / Setup | Proje tanıtımı, bağlantı bilgisi, privacy, ne değildir |

## Ortam değişkenleri

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `HOMENETIQ_BACKEND_URL` | `http://127.0.0.1:8080` | Backend kök URL'i |
| `HOMENETIQ_API_TOKEN` | (boş) | Opsiyonel. GET uçları auth istemiyor. |

## Çalıştırma

```bash
streamlit run dashboard/streamlit_app.py
# Pi üzerinde LAN'a açmak için
streamlit run dashboard/streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

## Boş veri yönetimi

- Backend kapalı: `st.error("Cannot reach backend...")`
- Metric yok: `st.info("No metrics received yet.")`
- Alan eksik: "No data yet for this field"

Cache 10s TTL; manuel yenileme için Streamlit `C` tuşu.

## Bilinen sınırlamalar

- Python 3.14 + starlette uyumluluk sorunu (sadece test ortamı).
- CORS yok (iç LAN).
- Hafif grafikler (line_chart, bar_chart, dataframe, metric).
- Cache TTL 10s.
