from langchain_community.document_loaders import DirectoryLoader

loader = DirectoryLoader("../", glob="**/*.md", use_multithreading=True)
docs = loader.load()
len(docs)