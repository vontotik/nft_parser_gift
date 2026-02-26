# nft_parser_gift
Telegram NFT Gift Parser Bot This bot monitors new Telegram NFT gifts and sends detailed information about them to a specified chat.

When a new gift is detected, the bot sends:

Gift name and link

Characteristics (model, backdrop, symbol) with rarity percentages

Number of issued copies

Current prices in TON, USDT, RUB (from telegifter.ru)

Owner information (if available) and permanent links to the owner

Buttons to quickly view the gift, the owner's profile, and the price page

The bot automatically determines the last issued number and continues monitoring from there. It supports multiple gifts simultaneously and also watches pre‑market gifts; when a pre‑market gift becomes available, it is automatically added to active monitoring.
