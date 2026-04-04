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

## Premium System
- Ucretsiz: Gunde 3 kupon, Banko + Orta seviye
- Premium (99TL/ay): Sinirsiz kupon, tum seviyeler
- Manuel onay: Kullanici dekont gonderir, admin onaylar

## Tech Stack
- Backend: FastAPI + Python
- Database: MongoDB (Motor async)
- Bot: python-telegram-bot
- AI: Emergent Integrations (GPT-5.2)
- Frontend: React (admin dashboard)

## Bot Commands
- /start - Bot baslat
- /kupon - Kupon olustur
- /maclar - Bugunku maclari gor
- /kuponlarim - Kuponlarimi gor
- /premium - Premium bilgi
- /odemeyaptim - Dekont gonder
- /help - Yardim
- /admin_payments - (Admin) Bekleyen odemeler
- /approve_XXX - (Admin) Odeme onayla
- /reject_XXX - (Admin) Odeme reddet

## Completed (April 2026)
- [x] FastAPI + React + MongoDB setup
- [x] Telegram bot with /start, /kupon commands
- [x] API-Football real match data integration
- [x] AI Analyzer with fallback parsing
- [x] Coupon success tracking with inline buttons
- [x] Cache Manager (6hr cache, 4 req/day limit)
- [x] League prioritization (top 5 leagues)
- [x] Premium membership system (manual approval)
- [x] Premium restrictions (3 free coupons, Zor locked)
- [x] /maclar command
- [x] All premium handlers registered
- [x] Daily coupon count tracking

## Backlog
- P2: Kullanici istatistikleri / Skor tablosu
- P3: React Admin paneli (premium onay yonetimi)
- Refactor: telegram_bot.py handler'lari ayri dosyalara bolme
