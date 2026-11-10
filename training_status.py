"""Read training history without loading a model or changing checkpoints."""
import bootstrap
import argparse,json
from pathlib import Path
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path(__file__).parent/'models/balanced-v1');a=parser.parse_args()
    path=a.output/'history.jsonl'
    if not path.exists():print('这个实验还没有完成一轮验证。请检查终端或数据是否准备完成。');return
    history=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    if not history:print('还没有记录');return
    latest=history[-1];best=max(history,key=lambda r:r['balanced_accuracy'])
    correct,total=latest['correct'],latest['total']
    print(f"已经完成：{latest['epoch']}轮；累计更新：{latest['step']}次")
    print(f"最近验证：真人{correct[0]}/{total[0]}张预测正确；AI{correct[1]}/{total[1]}张预测正确")
    print(f"平衡准确率：{latest['balanced_accuracy']:.1%}；真人误报率：{1-correct[0]/total[0]:.1%}；AI漏检率：{1-correct[1]/total[1]:.1%}")
    print(f"最高平衡准确率：{best['balanced_accuracy']:.1%}，首次出现在第{best['epoch']}轮")
    if len(history)>=5 and len(set(r['balanced_accuracy'] for r in history[-5:]))==1:print('最近5轮平衡准确率没有变化；不要仅靠追加轮数判断效果提升。')
    print('这是验证集成绩，不能直接当作系统或未知生成器准确率。')
if __name__=='__main__':main()
