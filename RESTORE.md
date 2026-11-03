# Dreamy Earth: tiklash qo'llanmasi (RESTORE)

## Nima qayerda
- Kod: GitHub `kingakbarov76-bit/ai-video-automation` (branch `main`, barqaror nusxa: branch `stable-2026-11-03`).
- Shorts serveri: Render web service `yt-auto-shorts` (srv-dbkrcsnf3r2c73fnj4b0), https://yt-auto-shorts.onrender.com
- Jadval: GitHub Actions `ping.yml` har 4 soatda `/run` ni ochadi.
- Kalitlar: faqat Render Environment (va `.env`, repo'da YO'Q). Ro'yxati: `.env.example`.

## Server ishlamasa
1. Render > yt-auto-shorts > Events/Logs ni ko'ring. `/status` va `/analyze` sahifalari ham bor.
2. Qayta ishga tushirish: Render > Manual Deploy > Deploy latest commit.
3. Kod buzilgan bo'lsa: `git checkout stable-2026-11-03 (branch)` (yoki `git revert`) va push qiling.

## YouTube ruxsati tugasa (invalid_grant)
`/auth` sahifasini oching, havola orqali ruxsat bering, `code=` ni sahifaga `?code=...` qilib qo'shing, chiqqan REFRESH TOKENni Render Environment'da `YT_REFRESH_TOKEN` ga yozing.

## Noldan, boshqa serverga ko'chirish (VPS)
1. `git clone` repo, `cp .env.example .env` va kalitlarni to'ldiring.
2. `docker compose up -d` (shorts + live ikkalasi).
3. Efir uchun YouTube'da jonli efirni yoqing, `STREAM_KEY` ni `.env` ga qo'ying.

## Muhim cheklovlar
- Render bepul rejasida oylik trafik ~5 GB bo'lishi mumkin: bitta video ~6-22 MB. Oylik > 3,5 GB bo'lsa yuklash sonini kamaytiring.
- YouTube API kvotasi: kuniga 10 000 birlik, bitta yuklash 1600.
- Google loyiha "Testing" rejimida bo'lsa ruxsat 7 kunda tugaydi.

## Musiqa kutubxonasi
- AI treklar (ACE-Step 1.5, Hugging Face Space `ACE-Step/Ace-Step-v1.5`) kuniga 1 marta 4 tadan yaratiladi (bepul ZeroGPU limiti).
- Saqlanadi: shu repo, branch `music-library`, papka `music/` (`_state.json` keyingi urinish vaqti). Bu branch deploy qilmaydi.
- Render env: `HF_TOKEN` (o'qish), `GH_PAT` (repo'ga yozish). Kutubxona bo'sh bo'lsa ichki sintez musiqa ishlatiladi.

## Jadval
- `ping.yml` har 4 soatlik slotda 3 marta (:07, :27, :47) `/run` ni ochadi. Server oxirgi yuklash 150 daqiqadan yaqin bo'lsa o'tkazib yuboradi (YouTube'dan tekshiradi), shuning uchun dublikat bo'lmaydi.
