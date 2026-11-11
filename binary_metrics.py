"""Pure binary counts, deliberately independent of model/runtime libraries."""
def statistics(results):
    real=[r for r in results if r['label']==0];fake=[r for r in results if r['label']==1]
    fp=sum(r['predicted']==1 for r in real);fn=sum(r['predicted']==0 for r in fake)
    fpr=fp/len(real) if real else None;fnr=fn/len(fake) if fake else None
    return dict(n=len(results),real_count=len(real),fake_count=len(fake),false_positives=fp,false_negatives=fn,real_false_positive_rate=fpr,fake_miss_rate=fnr,balanced_accuracy=1-(fpr+fnr)/2 if real and fake else None,accuracy=sum(r['label']==r['predicted'] for r in results)/len(results) if results else None)
