# Clinical routing boundary

The implemented routing function uses only explicit boolean workflow flags provided by the caller. It does not infer a condition, estimate risk from symptoms or images, recommend treatment, or make a diagnosis. The biomechanics function measures normalized coordinate path length from supplied landmarks; it does not detect landmarks from images or interpret movement clinically.

No TensorFlow/PyTorch model or clinical computer-vision classifier is included. Model weights, data provenance, clinical validity, bias evaluation, performance monitoring, regulatory classification, and intended-use constraints must be established and independently validated before any such model can be used in care. Do not substitute arbitrary weights or unvalidated inference for this workflow.
