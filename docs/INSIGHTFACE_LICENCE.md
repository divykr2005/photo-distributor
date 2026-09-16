# InsightFace Model Licence Notice

## Summary

This project uses the **InsightFace** library and its pre-trained model weights
(`buffalo_l`) for facial embedding extraction and matching.

## Licence Split — Code vs. Weights

| Component | Licence |
|-----------|---------|
| InsightFace Python library (`insightface` pip package, source code) | MIT Licence |
| Pre-trained model weights (e.g. `buffalo_l`, `antelopev2`) | **Separate non-commercial licence** |

**The MIT licence on the InsightFace code does NOT grant permission to use
the published model weights for commercial purposes.**

## What You Must Do Before Commercial Deployment

1. Review the model-use terms at:
   <https://github.com/deepinsight/insightface/tree/master/model_zoo#model-zoo>
   and
   <https://www.insightface.ai/solutions/face-recognition-licensing>

2. Contact InsightFace / DeepInsight to obtain a commercial licence for the
   specific model weights used by this project (`buffalo_l`).

3. Retain written evidence of the licence grant covering:
   - The exact model name and version (`buffalo_l`)
   - The intended commercial use case (event photo matching / distribution)
   - The territory / jurisdiction of deployment

4. Reference the licence number/date in this file once obtained.

## Current Status

- **Non-commercial pilots only** until a commercial model licence is obtained.
- Do **not** run a paid/ticketed event with biometric matching until step 3 above
  is complete and documented here.

## Reference Links

- InsightFace repository: <https://github.com/deepinsight/insightface>
- Model zoo: <https://github.com/deepinsight/insightface/blob/master/model_zoo/README.md>
- Commercial licensing: <https://www.insightface.ai/solutions/face-recognition-licensing>
