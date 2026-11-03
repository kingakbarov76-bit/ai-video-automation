# Dreamy Earth: tiklash qo'llanmasi (RESTORE)

## Nima qayerda
- Kod: GitHub `kingakbarov76-bit/ai-video-automation` (branch `main`, barqaror nusxa: branch `stable-2026-11-03`).
- Shorts serveri: Render web service `yt-auto-shorts` (srv-dbkrcsnf3r2c73fnj4b0), https://yt-auto-shorts.onrender.com
- Jadval: cron-job.org (foydalanuvchi hisobi) "Dreamy Earth" jadvali `/run` ni ochadi (Asia/Tashkent, `0,5 */4 * * *`).
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
- YouTube API kvotasi: kuniga 10 000 birlik (amalda kuniga 8 ta yuklash ishladi).
- Google loyiha "Testing" rejimida bo'lsa ruxsat HAR 7 KUNDA tugaydi; "Publish app" qilinsa bu muammo yo'qoladi.

## Musiqa kutubxonasi
- AI treklar (ACE-Step 1.5, Hugging Face Space `ACE-Step/Ace-Step-v1.5`) kuniga 1 marta 4 tadan yaratiladi (bepul ZeroGPU limiti).
- Saqlanadi: shu repo, branch `music-library`, papka `music/` (`_state.json` keyingi urinish vaqti). Bu branch deploy qilmaydi.
- Render env: `HF_TOKEN` (o'qish), `GH_PAT` (repo'ga yozish). Kutubxona bo'sh bo'lsa ichki sintez musiqa ishlatiladi.

## Jadval
- Asosiy: cron-job.org, har 4 soatda ikki marta (:00 va :05). Uxlab yotgan server 30 soniyada javob bermasligi mumkin (cron-job.org buni xato deb sanaydi va ~25 ketma-ket xatodan keyin jadvalni o'chiradi); :05 dagi ochish server uyg'oq paytiga to'g'ri keladi va muvaffaqiyatli bo'ladi, shuning uchun jadval o'chmaydi.
- Server har uyg'onishda o'zi run boshlaydi; oxirgi yuklash 150 daqiqadan yaqin bo'lsa yoki 24 soatda 12 ta bo'lsa o'tkazib yuboradi (YouTube'dan tekshiradi), dublikat bo'lmaydi.
- GitHub Actions `ping.yml` jadvali bu repoda ishlamaydi; faqat push bilan ishlaydi (zaxira: `ping.yml` ga izoh qatori qo'shib push qilish serverni qayta deploy qiladi).
