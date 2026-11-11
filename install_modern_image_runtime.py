"""Install the image worker dependencies separately from the main application."""
import bootstrap,subprocess,sys,os
root=bootstrap.ROOT;env=dict(os.environ,TEMP=str(root/'runtime/tmp'),TMP=str(root/'runtime/tmp'))
subprocess.run([sys.executable,'-m','pip','install','--upgrade','--target',str(root/'runtime/smaug-packages'),'--no-deps','-r',str(root/'requirements-modern-image.txt')],cwd=root,env=env,check=True)
