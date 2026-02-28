import modal

app = modal.App()
image = modal.Image.debian_slim().pip_install("transformers", "torch")

@app.function(gpu="A10G", image=image, min_containers=1)
def score_article(text: str) -> float:
    from transformers import pipeline
    pipe = pipeline("text-classification", model="ProsusAI/finbert")
    return pipe(text)[0]

@app.local_entrypoint()
def main():
    print(score_article.remote("I don't like this stock. Type shitty earnings report."))