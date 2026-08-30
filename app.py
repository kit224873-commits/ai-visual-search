from flask import Flask, request, jsonify, Response
from google import genai
import os
import base64
import json
import re
from urllib.parse import quote_plus

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing.")

client = genai.Client(api_key=API_KEY)
MODEL = "gemini-3.6-flash"


HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>AI Visual Search</title>

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f5f6f8;
    color: #111;
}

.container {
    width: 92%;
    max-width: 950px;
    margin: auto;
    padding: 30px 0 50px;
}

header {
    text-align: center;
    margin-bottom: 28px;
}

.logo {
    font-size: 42px;
    font-weight: 800;
    margin: 0;
}

.tagline {
    color: #666;
    margin-top: 8px;
}

.card {
    background: white;
    border-radius: 22px;
    padding: 24px;
    box-shadow: 0 10px 30px rgba(0,0,0,.07);
}

.upload {
    border: 2px dashed #d4d4d4;
    border-radius: 18px;
    padding: 38px 18px;
    text-align: center;
}

.icon {
    font-size: 48px;
}

.pick {
    display: inline-block;
    margin-top: 15px;
    padding: 14px 24px;
    background: #111;
    color: white;
    border-radius: 11px;
    font-weight: 700;
    cursor: pointer;
}

#file {
    display: none;
}

#preview {
    display: none;
    width: 100%;
    max-height: 420px;
    object-fit: contain;
    margin: 22px 0;
    border-radius: 15px;
}

#find {
    display: none;
    width: 100%;
    padding: 15px;
    border: 0;
    border-radius: 11px;
    background: #111;
    color: white;
    font-size: 16px;
    font-weight: 700;
    cursor: pointer;
}

#find:disabled {
    opacity: .5;
}

#loading {
    display: none;
    text-align: center;
    margin: 22px 0;
    font-weight: 700;
}

#error {
    color: #c00000;
    text-align: center;
    margin-top: 18px;
}

#result {
    display: none;
    margin-top: 30px;
}

.result-name {
    font-size: 28px;
    font-weight: 800;
}

.category {
    display: inline-block;
    margin-top: 10px;
    padding: 7px 12px;
    border-radius: 18px;
    background: #eceeef;
    font-size: 13px;
    font-weight: 700;
}

.description {
    margin-top: 14px;
    color: #555;
    line-height: 1.5;
}

.query {
    margin-top: 14px;
    padding: 14px;
    background: #f1f2f4;
    border-radius: 12px;
    font-weight: 700;
}

.products-title {
    margin-top: 32px;
}

.products {
    display: grid;
    grid-template-columns: repeat(
        auto-fit,
        minmax(220px, 1fr)
    );
    gap: 16px;
    margin-top: 18px;
}

.product {
    border: 1px solid #e1e1e1;
    border-radius: 16px;
    overflow: hidden;
    background: white;
}

.product-top {
    height: 150px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #f0f1f3;
    font-size: 52px;
}

.product-body {
    padding: 16px;
}

.product-name {
    font-weight: 800;
    line-height: 1.35;
}

.product-store {
    margin-top: 7px;
    color: #777;
    font-size: 14px;
}

.product-price {
    margin-top: 9px;
    font-size: 19px;
    font-weight: 800;
}

.preview-label {
    margin-top: 7px;
    color: #999;
    font-size: 11px;
}

.view {
    display: block;
    margin-top: 13px;
    padding: 12px;
    border-radius: 10px;
    background: #111;
    color: white;
    text-decoration: none;
    text-align: center;
    font-weight: 700;
}

.again {
    width: 100%;
    margin-top: 24px;
    padding: 13px;
    border: 1px solid #ddd;
    background: white;
    border-radius: 10px;
    font-weight: 700;
    cursor: pointer;
}

.made {
    text-align: center;
    margin-top: 24px;
    color: #888;
    font-size: 13px;
}

@media (max-width: 600px) {
    .container {
        width: 94%;
    }

    .logo {
        font-size: 34px;
    }

    .card {
        padding: 15px;
    }
}
</style>
</head>

<body>

<div class="container">

<header>
    <h1 class="logo">AI Visual Search</h1>
    <div class="tagline">Find what you see.</div>
</header>

<div class="card">

<div class="upload">

    <div class="icon">📷</div>

    <h2>Upload a photo</h2>

    <p>We'll identify it and find similar products.</p>

    <label class="pick" for="file">Choose Photo</label>

    <input id="file" type="file" accept="image/*">

    <img id="preview" alt="Preview">

    <button id="find">Find This</button>

</div>

<div id="loading">
    🤖 Finding your match...
</div>

<div id="error"></div>

<div id="result">

    <div id="resultName" class="result-name"></div>

    <div id="category" class="category"></div>

    <div id="description" class="description"></div>

    <div id="query" class="query"></div>

    <h2 class="products-title">Similar Products</h2>

    <div id="products" class="products"></div>

    <button id="again" class="again">
        Search Another Photo
    </button>

</div>

</div>

<div class="made">
    Made by AK
</div>

</div>

<script>

const file = document.getElementById("file");
const preview = document.getElementById("preview");
const findButton = document.getElementById("find");
const loading = document.getElementById("loading");
const errorBox = document.getElementById("error");
const result = document.getElementById("result");
const resultName = document.getElementById("resultName");
const category = document.getElementById("category");
const description = document.getElementById("description");
const query = document.getElementById("query");
const products = document.getElementById("products");
const again = document.getElementById("again");


file.addEventListener("change", function () {

    const selected = file.files[0];

    if (!selected) return;

    preview.src = URL.createObjectURL(selected);
    preview.style.display = "block";
    findButton.style.display = "block";

    result.style.display = "none";
    errorBox.textContent = "";
});


findButton.addEventListener("click", async function () {

    const selected = file.files[0];

    if (!selected) {
        errorBox.textContent = "Please choose a photo first.";
        return;
    }

    const form = new FormData();
    form.append("image", selected);

    findButton.disabled = true;
    loading.style.display = "block";
    errorBox.textContent = "";
    result.style.display = "none";

    try {

        const response = await fetch("/identify", {
            method: "POST",
            body: form
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Something went wrong.");
        }

        resultName.textContent =
            data.name || "Unknown item";

        category.textContent =
            data.category || "Unknown";

        description.textContent =
            data.description || "";

        query.textContent =
            "Search: " + (data.query || data.name || "");

        products.innerHTML = "";

        const search = encodeURIComponent(
            data.query || data.name || ""
        );

        const stores = [
            {
                store: "Google Shopping",
                icon: "🛒",
                url:
                    "https://www.google.com/search?tbm=shop&q=" +
                    search
            },
            {
                store: "eBay",
                icon: "🛍️",
                url:
                    "https://www.ebay.com/sch/i.html?_nkw=" +
                    search
            },
            {
                store: "Amazon",
                icon: "📦",
                url:
                    "https://www.amazon.com/s?k=" +
                    search
            },
            {
                store: "Daraz",
                icon: "🛒",
                url:
                    "https://www.daraz.pk/catalog/?q=" +
                    search
            }
        ];

        stores.forEach(function (item) {

            const card =
                document.createElement("div");

            card.className = "product";

            card.innerHTML = `
                <div class="product-top">
                    ${item.icon}
                </div>

                <div class="product-body">

                    <div class="product-name">
                        ${data.name}
                    </div>

                    <div class="product-store">
                        ${item.store}
                    </div>

                    <div class="product-price">
                        Search current listings
                    </div>

                    <div class="preview-label">
                        LIVE SEARCH
                    </div>

                    <a
                        class="view"
                        href="${item.url}"
                        target="_blank"
                        rel="noopener noreferrer">
                        View Products
                    </a>

                </div>
            `;

            products.appendChild(card);
        });

        result.style.display = "block";

    } catch (e) {

        errorBox.textContent =
            "Error: " + e.message;

    } finally {

        findButton.disabled = false;
        loading.style.display = "none";
    }
});


again.addEventListener("click", function () {

    file.value = "";
    preview.src = "";
    preview.style.display = "none";
    findButton.style.display = "none";
    result.style.display = "none";
    errorBox.textContent = "";

});
</script>

</body>
</html>
"""


@app.route("/")
def home():
    return Response(HTML, mimetype="text/html")


@app.route("/identify", methods=["POST"])
def identify():

    if "image" not in request.files:
        return jsonify({
            "error": "Please upload a photo."
        }), 400

    uploaded = request.files["image"]

    if not uploaded.filename:
        return jsonify({
            "error": "Please choose a photo."
        }), 400

    try:

        image_bytes = uploaded.read()

        if not image_bytes:
            return jsonify({
                "error": "The image is empty."
            }), 400

        mime_type = uploaded.mimetype or "image/jpeg"

        image_data = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        prompt = """
You are a visual shopping assistant.

Analyze the image carefully.

Return ONLY valid JSON:

{
  "name": "best specific identification",
  "category": "specific category",
  "description": "short useful description",
  "query": "short search query"
}

Rules:
- Identify the main thing the user would want to search for.
- Recognize characters when clearly visible.
- Identify products when possible.
- If it is artwork, identify the artwork type.
- Never invent a brand or model.
- Use a short search query suitable for shopping.
- Do not use markdown.
"""

        response = client.models.generate_content(
            model=MODEL,
            contents=[
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": image_data
                    }
                },
                prompt
            ]
        )

        text = (response.text or "").strip()

        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        data = json.loads(text)

        return jsonify({
            "success": True,
            "name": str(data.get("name", "Unknown item")),
            "category": str(data.get("category", "Unknown")),
            "description": str(data.get("description", "")),
            "query": str(
                data.get(
                    "query",
                    data.get("name", "")
                )
            )
        })

    except Exception as e:

        print("ERROR:", repr(e))

        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":

    print("==============================")
    print("AI VISUAL SEARCH")
    print("==============================")
    print("http://127.0.0.1:5000")
    print("==============================")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )