# HomeNetIQ — Kalite Motoru (Türkçe)

> 🇬🇧 English: [docs/QUALITY_ENGINE.md](../QUALITY_ENGINE.md)

Bu doküman v1'deki kalite puanı, issue tespiti, kök neden sınıflandırması
ve öneri üretimi mantığını açıklar.

## 1. Skor nasıl hesaplanıyor

`classify_quality(metric_type, payload)` 4 değer döner:

- `quality`: `"good"` (80-100), `"warning"` (50-79), `"poor"` (0-49)
- `issues`: makine-okunabilir kod listesi
- `quality_score`: 0-100 integer
- `explanations`: her issue için kısa gerekçe

Başlangıç: 100 puan. Her tespit edilen issue belirli bir ceza uygular
(örn. `weak_signal` -25, `low_snr` -15). Birden fazla "severe" issue
birikirse kümülatif ceza uygulanır.

| Severe issue sayısı | Ek ceza |
|---|---|
| 1 | 0 |
| 2 | -5 |
| 3+ | -10 |

Son olarak skor `[0, 100]` aralığına sıkıştırılır ve kategoriye çevrilir.

## 2. Issue code listesi

Bkz. İngilizce dokümandaki tablo (aynı eşikler geçerli).

## 3. Root cause listesi

`classify_root_cause(metric_type, payload, issues)` şu değerlerden birini
döner: `healthy`, `wifi_signal_issue`, `wifi_congestion_issue`,
`local_ap_issue`, `gateway_or_lan_issue`, `wan_or_isp_issue`, `dns_issue`,
`single_device_issue`, `probe_or_backend_issue`, `unknown_issue`.

Sıra önemlidir: en spesifik koşul en üstte kontrol edilir.

## 4. Öneri (recommendation) mantığı

`recommend(issues, root_cause)` deterministik bir sözlükten öneri üretir.
Önce root cause'un genel önerisi, sonra her issue için ek ipucu
eklenir. Listede tekrarsız döner.

Örnekler İngilizce dokümandakiyle aynıdır.

## 5. Payload alan eşlemesi

| Mantıksal alan | Kabul edilen payload anahtarları |
|---|---|
| RSSI | `rssi`, `signal` |
| Packet loss | `packet_loss_percent`, `packet_loss` |
| Band | `band` (herhangi bir string normalize edilir) |

## 6. Bilinen sınırlamalar (v1)

- **Tek cihaz, tek anlık görüntü:** engine yalnızca tek bir payload'ı
  değerlendirir.
- **Skor / kategori ayrımı sınırda:** sadece `slow_dns` skoru -10
  düşürür, bu nedenle `quality` hâlâ "good" olabilir.
- **Öneri statik:** kurulum/cihaza özel değil.
- **Çoklu payload korelasyonu yok.**
- **Eşikler sabit:** `Thresholds` dataclass; YAML/env override henüz yok.

## 7. API sözleşmesi (geriye uyumlu)

`POST /api/v1/metrics` response: `quality`, `issues`, `root_cause` (eski)
+ `quality_score`, `explanations`, `recommendations` (yeni, opsiyonel).
