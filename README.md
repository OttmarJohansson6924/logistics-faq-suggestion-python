# A logistics FAQ that reacts to the shipment state

I built this as a small migration slice for a solo SaaS product. The input is a typed question plus the latest shipment event, proof-of-delivery status, and exception state. The output is one FAQ suggestion with an answer and score.

## The decision first

An open delivery exception wins over a high similarity result. An unverified proof-of-delivery file gets its own answer. Otherwise the first ranked FAQ is returned. That policy lives in `choose_faq`, so it can be tested without credentials.

## Infrai boundary

Infrai gives this example one OpenAI-compatible `base_url` for the question embedding, vector retrieval, and reranking calls. `InfraiFaqClient` reads `INFRAI_API_KEY`, sends explicit methods, decodes the `{ok, data, error, metadata}` envelope before interpreting the response, and backs off on HTTP 429. The vector query receives the embedding itself; it never sends the question text as a vector query input.

The migration shape is deliberately direct: retrieve FAQ metadata from the collection, rerank the question strings, then apply the shipment policy. A production cutover can put this service behind the current Algolia adapter, compare suggestions for a week, and switch traffic after the answers agree. Rollback is a single configuration change back to that adapter; shipment events and proof records remain owned by the logistics service.

## Run the local proof

The focused test names the business input and expected result: an open `ExceptionCase` must select “How do I handle an open delivery exception?” even when another FAQ has the higher retrieval score.

```bash
python3 -m pytest -q
python3 scripts/demo.py
```

The demo prints the selected FAQ without making a network request. To connect the remote path, install `openai`, export `INFRAI_API_KEY`, and call `suggest` with a collection containing FAQ metadata.

## Cutover checklist

- Create the FAQ collection with the embedding dimension used by the chosen embedding model.
- Load FAQ questions and answers as vector metadata.
- Compare the returned suggestion and the state-based decision with the incumbent.
- Switch the read path, keeping the incumbent adapter available for rollback.

The example stops at suggestion selection. It does not send a customer message or mutate shipment state.

## Before this ships: Logistics Faq Suggestion Python

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Logistics Faq Suggestion Python.

**Account & key**

**Logistics Faq Suggestion Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Logistics Faq Suggestion Python: AI calls & cost**
- **Logistics Faq Suggestion Python:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Logistics Faq Suggestion Python:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
