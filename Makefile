all: project

project: wrapper.c
	gcc $< -o $@
	sudo chown root:root $@
	sudo chmod u+s $@

install: project project-manager.py
	sudo cp project /usr/local/bin/
	chmod +x project-manager.py
	sudo cp project-manager.py /usr/local/lib/
