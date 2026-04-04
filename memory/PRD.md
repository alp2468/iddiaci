# Telegram Bahis Kupon Botu - PRD

## Problem Statement
Belirli liglerdeki futbol maclarini analiz edip, AI destekli tahminlerle gunluk bahis kuponlari olusturan bir Telegram botu.

## Core Features
- 9 ligden gercek mac verisi (API-Football)
- AI destekli tahminler (GPT-5.2 via Emergent LLM)
- 3 risk seviyesi: Banko, Orta, Zor
- Mac cache sistemi (6 saatlik, gunluk 4 API cagrisi)
- Kupon basari takibi (kullanici geri bildirimi)
- Manuel Premium uyelik sistemi
- Admin yonetim paneli (Telegram uzerinden)

## Premium System
- Ucretsiz: Gunde 3 kupon, Banko + Orta seviye
- Premium (99TL/ay): Sinirsiz kupon, tum seviyeler
- Admin: Sinirsiz, tum limitler bypass
- Manuel onay: Kullanici dekont gonderir, admin onaylar

## Tech Stack
- Backend: FastAPI + Python
- Database: MongoDB (Motor async)
- Bot: python-telegram-bot
- AI: Emergent Integrations (GPT-5.2)
- Frontend: React (admin dashboard)

## Bot Commands
### Kullanici Komutlari
- /start - Bot baslat
- /kupon - Kupon olustur
- /maclar - Bugunku maclari gor
- /kuponlarim - Kuponlarimi gor
- /premium - Premium bilgi
- /odemeyaptim - Dekont gonder
- /help - Yardim

### Admin Komutlari
- /admin - Admin paneli (istatistikler)
- /admin_payments - Bekleyen odemeler
- /admin_users - Kullanici listesi
- /admin_cache - Cache yenile
- /admin_premium @user - Manuel premium ver
- /admin_stats - Detayli istatistikler
- /approve_XXX - Odeme onayla
- /reject_XXX - Odeme reddet

## Completed (April 2026)
- [x] FastAPI + React + MongoDB setup
- [x] Telegram bot with all commands
- [x] API-Football real match data integration
- [x] AI Analyzer with fallback parsing
- [x] Coupon success tracking with inline buttons
- [x] Cache Manager (6hr cache, 4 req/day limit)
- [x] League prioritization (top 5 leagues)
- [x] Premium membership system (manual approval)
- [x] Premium restrictions (3 free coupons, Zor locked)
- [x] /maclar command
- [x] Admin bypass (unlimited for admin)
- [x] Admin panel commands (/admin, /admin_users, /admin_cache, /admin_premium, /admin_stats)
- [x] Daily coupon count tracking

## Backlog
- P2: Kullanici istatistikleri / Skor tablosu
- P3: React Admin paneli (premium onay yonetimi web uzerinden)
- Refactor: telegram_bot.py handler'lari ayri dosyalara bolme
