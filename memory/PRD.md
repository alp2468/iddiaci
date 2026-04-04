# Telegram Bahis Kupon Botu - PRD

## Problem Statement
Belirli liglerdeki futbol maclarini analiz edip, AI destekli tahminlerle bahis kuponlari olusturan bir Telegram botu.

## Core Features
- 9 ligden gercek mac verisi (API-Football, buyuk 5 lig oncelikli)
- AI destekli tahminler (GPT-5.2 via Emergent LLM)
- 3 risk seviyesi: Banko, Orta, Zor
- Mac cache sistemi (6 saatlik, gunluk 4 API cagrisi)
- Kupon basari takibi
- Manuel Premium uyelik sistemi (30 gun)
- Admin yonetim paneli (Telegram + React Web)
- Kullanici istatistikleri

## Premium System
- Ucretsiz: TOPLAM 3 kupon hakki, Banko + Orta seviye
- Premium (99TL/ay): Sinirsiz kupon, tum seviyeler, 30 gun
- Admin: Sinirsiz, tum limitler bypass
- Otomatik sure takibi: 3 gun kala hatirlatma, suresi dolunca otomatik kaldirma

## Bot Commands
### Kullanici
- /start, /kupon, /maclar, /kuponlarim, /istatistik, /premium, /odemeyaptim, /help

### Admin
- /admin, /admin_payments, /admin_users, /admin_cache, /admin_premium, /admin_stats

## Admin Panel (React Web)
- Genel Bakis: Tum istatistikler (kullanici, kupon, gelir, basari orani)
- Kullanicilar: Liste, premium ver/kaldir butonlari
- Odemeler: Onayla/Reddet butonlari

## Completed (April 2026)
- [x] FastAPI + React + MongoDB setup
- [x] Telegram bot tum komutlar
- [x] API-Football buyuk 5 lig oncelikli
- [x] AI Analyzer
- [x] Kupon basari takibi
- [x] Cache Manager
- [x] Premium sistem (toplam 3 hak, 30 gun abonelik, otomatik sure takibi)
- [x] Admin bypass (sinirsiz)
- [x] Admin panel komutlari (Telegram)
- [x] Admin panel (React Web - overview/users/payments)
- [x] Kullanici istatistikleri (/istatistik)
- [x] Rastgele kupon kombinasyonlari

## Backlog
- Refactor: telegram_bot.py handler'lari ayri dosyalara bolme
