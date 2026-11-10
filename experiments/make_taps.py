"""Provenance of gn/taps.json. Needs a checkout of anttiluode/GeometricNeuronOriginReview:

    python experiments/make_taps.py /path/to/GeometricNeuronOriginReview

For every square size q from -200 to 399 the ARCHIVED CheckerboardNode and ImageToVectorNode
(unchanged files from that repository) are run, and the first 16 values of the 256-vector are
stored. Those are the 16 splitter outputs. Outputs 0-3 summed are the table F of that repository.
"""
import json
import sys
from pathlib import Path

import numpy as np

origin = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(origin / "experiments"))
import ecg_causal_reduction as E  # noqa: E402

g = E.harness.Graph(overrides={3: {"output_dim": 256, "vector": np.zeros(256, dtype=np.float32)}})
taps = []
for q in range(-200, 400):
    img = E.image_for_q(g, q)
    g.i2v.pre_step()
    g.i2v.set_input("image_in", img, "image")
    g.i2v.step()
    taps.append([float(v) for v in g.i2v.get_output("vector_out")[:16]])
out = Path(__file__).resolve().parent.parent / "gn" / "taps.json"
out.write_text(json.dumps({"qmin": -200, "qmax": 399, "taps": taps}))
