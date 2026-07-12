from __future__ import annotations

from openai import OpenAI

from .schemas import PinCopy, ProductInput
from .settings import Settings


SYSTEM_PROMPT = '''
You are the copy engine for Smart Gear Lab, a Pinterest + Amazon affiliate media brand.
Create premium, useful, high-CTR English copy for a vertical 2:3 Pinterest product pin.

Hard rules:
- Sell the result, not the object.
- Never invent specifications, compatibility, performance, price, discount, rating, or review count.
- Use only facts supplied by the user. If facts are sparse, use category-level benefits without technical claims.
- Headline: 2-6 words, instantly readable on a phone.
- Exactly two bullets, each 2-6 words.
- Title: natural Pinterest SEO, maximum 100 characters.
- Description: natural English, useful, not spammy, and end with exactly:
  Affiliate links may earn commission.
- Alt text must describe what is actually shown.
- Hashtags: 10-15 specific tags, not broad junk tags.
- visual_prompt describes only a premium background scene. Do not include a product, logos, words, labels, icons, or typography.
- Avoid aggressive calls to action such as BUY NOW.
- Avoid prices, percentages, ratings, review counts, and unverifiable superlatives.
'''


def generate_pin_copy(product: ProductInput, settings: Settings) -> PinCopy:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    client = OpenAI(api_key=settings.openai_api_key)
    user_prompt = f'''
Product name: {product.product_name}
Known features and facts:
{product.features or "No verified technical specifications supplied."}

Audience: {product.audience}
Content cluster: {product.cluster}
Visual style: {product.style}

Create one Pinterest package. The product image will be composited separately,
so the background prompt must not contain the product itself.
'''
    response = client.responses.parse(
        model=settings.openai_text_model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        text_format=PinCopy,
    )
    if response.output_parsed is None:
        raise RuntimeError("OpenAI returned no structured copy.")
    return response.output_parsed
