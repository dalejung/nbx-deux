"""
c.MetaManager.submanager_post_save_hooks = ["nbx_deux.gist_hooks.gist_post_save_notebook"]
"""
from github import Auth, Github

from jupyter_server.services.contents.filemanager import FileContentsManager
from jupyter_server.utils import to_api_path
from nbx_deux.bundle_manager.bundle_nbmanager import BundleContentsManager
from .gist import GistService, model_to_files
from nbx_deux.config import GITHUB_TOKEN

service = None
if GITHUB_TOKEN:
    auth = Auth.Token(GITHUB_TOKEN)
    hub = Github(auth=auth)
    service = GistService(hub=hub)


def gist_post_save_notebook(model, os_path, contents_manager, **kwargs):
    if service is None:
        return

    # for now only support bundlenbmanager
    if not isinstance(contents_manager, (BundleContentsManager, FileContentsManager)):
        return

    api_path = to_api_path(os_path, contents_manager.root_dir)
    model_path = model['path']
    if model_path != api_path:
        print("uh. why?")
        return 

    model = contents_manager.get(api_path, content=True)

    gist_id = model['content']['metadata'].get('gist_id', None)
    if gist_id is None:
        return

    gist = service.get_gist(gist_id)
    if not service.is_owned(gist):
        return

    name = os_path.rsplit('/', 1)[-1]

    files = model_to_files(model)

    try:
        gist.save(description=name, files=files)
    except Exception:
        print(files)
        raise Exception('Error saving gist')
    else:
        msg = f"Saved notebook {api_path} {name} to gist {gist_id}"
        print(msg)
