import os
import json
import argparse

import numpy as np
import matplotlib.pyplot as plt

plt.style.use("matplotlib.mplstyle")

parser = argparse.ArgumentParser()
parser.add_argument('output_dirs', nargs='+',
                    help="List of dirs containting metrics.json files")
parser.add_argument('-t', '--title', default=None, help='Plot title.')
parser.add_argument('-o', '--output', default="./metrics",
                    help='Dir to save the plots.')
args = parser.parse_args()

metrics_dict = {}

for outdir in args.output_dirs:
    metrics = os.path.join(outdir, 'metrics.json')
    if not os.path.isfile(metrics):
        print("Not found:", metrics)
        continue

    # parse number of shots from abstracts_error_diversity_3shot
    try:
        shots = [int(word[0]) for word in outdir.split("/")[-1].split("_") if 'shot' in word]
    except:
        print("Cannot parse the number of shots:", outdir)
        continue
    
    # load metric
    with open(metrics) as fp:
        metrics_dict[shots[0]] = json.load(fp)

print("\nMetrics: ", metrics_dict, "\n")
os.makedirs(args.output, exist_ok=True)

x = metrics_dict.keys()

# Plot f-1 
y_llm = [metrics_dict[i]['llm']['F1'] for i in x]
y_nlp = [metrics_dict[i]['nlp']['F1'] for i in x]
outfile = os.path.join(args.output, "f1-score.png")

fig, ax = plt.subplots(figsize=(3.25, 2.5))
ax.plot(x, y_llm, 'rx--', label="LLM")
ax.plot(x, y_nlp, 'gx--', label="BERT")
ax.set(ylabel='F-1 score', xlabel='No. of shots')
if args.title is not None:
    ax.set_title(args.title)
ax.legend()
plt.tight_layout()
plt.savefig(outfile, dpi=600)
print("Save OK:", outfile)
plt.close()

# Plot precision
y_llm = [metrics_dict[i]['llm']['precision'] for i in x]
y_nlp = [metrics_dict[i]['nlp']['precision'] for i in x]
outfile = os.path.join(args.output, "precision.png")

fig, ax = plt.subplots(figsize=(3.25, 2.5))
ax.plot(x, y_llm, 'rx--', label="LLM")
ax.plot(x, y_nlp, 'gx--', label="BERT")
ax.set(ylabel='Precision', xlabel='No. of shots')
if args.title is not None:
    ax.set_title(args.title)
ax.legend()
plt.tight_layout()
plt.savefig(outfile, dpi=600)
print("Save OK:", outfile)
plt.close()


# Plot recall
y_llm = [metrics_dict[i]['llm']['recall'] for i in x]
y_nlp = [metrics_dict[i]['nlp']['recall'] for i in x]
outfile = os.path.join(args.output, "recall.png")

fig, ax = plt.subplots(figsize=(3.25, 2.5))
ax.plot(x, y_llm, 'rx--', label="LLM")
ax.plot(x, y_nlp, 'gx--', label="BERT")
ax.set(ylabel='Recall', xlabel='No. of shots')
if args.title is not None:
    ax.set_title(args.title)
ax.legend()
plt.tight_layout()
plt.savefig(outfile, dpi=600)
print("Save OK:", outfile)
plt.close()

print("Done")
