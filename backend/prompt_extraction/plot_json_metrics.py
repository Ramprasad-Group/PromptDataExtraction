import os
import json
import argparse
import pandas as pd
import matplotlib.pyplot as plt

from utils import Frame

plt.style.use("matplotlib.mplstyle")

parser = argparse.ArgumentParser()
parser.add_argument('output_dirs', nargs='+',
                    help="List of dirs containting metrics.json files")
parser.add_argument('-t', '--title', default=None, help='Plot title.')
parser.add_argument('-o', '--output', default="./metrics",
                    help='Dir to save the plots.')
parser.add_argument('-r', '--runs', default=1, type=int,
                    help='Number of runs, default 1')
args = parser.parse_args()


def plot_single_run(metrics : pd.DataFrame, figsize=(3.25, 2.2)):
    x = metrics[(metrics.api == 'llm')]['shots']

    # Plot f-1 
    y_llm = metrics[(metrics.api == 'llm')]['F1']
    y_nlp = metrics[(metrics.api == 'nlp')]['F1']
    outfile = os.path.join(args.output, "f1-score.png")

    fig, ax = plt.subplots(figsize=figsize)
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
    y_llm = metrics[(metrics.api == 'llm')]['precision']
    y_nlp = metrics[(metrics.api == 'nlp')]['precision']
    outfile = os.path.join(args.output, "precision.png")

    fig, ax = plt.subplots(figsize=figsize)
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
    y_llm = metrics[(metrics.api == 'llm')]['recall']
    y_nlp = metrics[(metrics.api == 'nlp')]['recall']
    outfile = os.path.join(args.output, "recall.png")

    fig, ax = plt.subplots(figsize=figsize)
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


def plot_multi_run(metrics : pd.DataFrame, figsize=(3.25, 2.5)):
    runs = metrics.run.unique()

    # Plot f-1 
    outfile = os.path.join(args.output, "f1-score.png")

    fig, ax = plt.subplots(figsize=figsize)
    for r in runs:
        mask = (metrics.run == r) & (metrics.api == 'llm')
        y_llm = metrics[mask]['F1']
        x = metrics[mask]['shots']
        ax.plot(x, y_llm, '.-', label="Run %d" %r)

    ax.set(ylabel='F-1 score', xlabel='No. of shots')
    if args.title is not None:
        ax.set_title(args.title)
    ax.legend()
    plt.tight_layout()
    plt.savefig(outfile, dpi=600)
    print("Save OK:", outfile)
    plt.close()

    # Plot precision
    outfile = os.path.join(args.output, "precision.png")

    fig, ax = plt.subplots(figsize=figsize)
    for r in runs:
        mask = (metrics.run == r) & (metrics.api == 'llm')
        y_llm = metrics[mask]['precision']
        x = metrics[mask]['shots']
        ax.plot(x, y_llm, '.-', label="Run %d" %r)

    ax.set(ylabel='Precision', xlabel='No. of shots')
    if args.title is not None:
        ax.set_title(args.title)
    ax.legend()
    plt.tight_layout()
    plt.savefig(outfile, dpi=600)
    print("Save OK:", outfile)
    plt.close()

    # Plot recall
    outfile = os.path.join(args.output, "recall.png")

    fig, ax = plt.subplots(figsize=figsize)
    for r in runs:
        mask = (metrics.run == r) & (metrics.api == 'llm')
        y_llm = metrics[mask]['recall']
        x = metrics[mask]['shots']
        ax.plot(x, y_llm, '.-', label="Run %d" %r)
    ax.set(ylabel='Recall', xlabel='No. of shots')
    if args.title is not None:
        ax.set_title(args.title)
    ax.legend()
    plt.tight_layout()
    plt.savefig(outfile, dpi=600)
    print("Save OK:", outfile)
    plt.close()

    print("Done")


run_no = 1
data = Frame()

for outdir in args.output_dirs:
    metrics_file = os.path.join(outdir, 'metrics.json')
    if not os.path.isfile(metrics_file):
        print("Not found:", metrics_file)
        continue

    # parse number of shots from abstracts_error_diversity_3shot
    try:
        shots = [int(word[0]) for word in outdir.split("/")[-1].split("_") if 'shot' in word]
        shots = shots[0]
    except:
        print("Cannot parse the number of shots:", outdir)
        continue
    
    if "_run" in outdir:
        try:
            run_no = [int(word[-1]) for word in outdir.split("/")[-1].split("_") if 'run' in word]
            run_no = run_no[0]
        except:
            print("Cannot parse the run number:", outdir)
            continue

    # load metric
    with open(metrics_file) as fp:
        metrics = json.load(fp)

    for k, v in metrics.items():
        data.add(run=run_no, api=k, shots=shots,
                 F1=v['F1'], precision=v['precision'],
                 recall=v['recall'], tokens=v['token_usage'])

print(data.df)
os.makedirs(args.output, exist_ok=True)
data.df.to_csv(os.path.join(args.output, "metrics.csv"), index=False)

if args.runs <= 1:
    plot_single_run(data.df)
else:
    plot_multi_run(data.df)
