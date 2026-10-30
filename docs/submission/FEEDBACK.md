# Technology feedback worksheet

Do not submit invented runtime feedback. The integration observations below come from code and tests; the live-call section must be completed from an actual account-backed run.

## Nebius Token Factory: implementation observations

The OpenAI-compatible chat-completions interface allowed a small dedicated HTTP adapter. The adapter requests JSON, bounds response size, disables retries and redirects, and records observed model/usage metadata. Explicit handling for non-200 responses, incomplete output, network errors, timeouts, and malformed JSON helped us preserve honest failure states.

Suggested improvement: make model-specific structured-output behavior, response-model naming, and request-ID availability especially clear in the model documentation, with examples of error and truncated responses. These are documentation/product requests, not claims that we observed a production defect.

## NVIDIA Nemotron: evaluation boundary

The intended role is explaining the limits of computed descriptors. We require the allowed evidence ID and a narrow JSON structure. We do not treat that schema check as factual verification. The next evaluation needs expert review of whether the model consistently avoids inferring clinical efficacy, safety, or experimental results.

## Fill from the real run before submission

- UTC time, exact model requested, actual model returned:
- Nebius endpoint:
- Observed latency and reported usage:
- Did the structured response pass the application schema?
- Did the prose stay within the supplied evidence?
- Concrete successful behavior, quoting at most a short relevant excerpt:
- Concrete friction or failure, if actually observed:
- Change that would most improve this workflow:
- Account/credit experience actually observed:

Never include API keys, passwords, private billing data, or unsupported benchmark comparisons.
