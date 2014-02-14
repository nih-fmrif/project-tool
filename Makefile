all: project manpage

project: wrapper.c
	gcc $< -o $@

project.1: project.1.md
	pandoc -s -t man $< > project.1
	gzip -f project.1

manpage: project.1

install: project project-manager.py project.1.gz
	sudo install -g 0 -o 0 -m 0644 project.1.gz /usr/local/share/man/man1
	sudo install -g 0 -o 0 -m 4755 project /usr/local/bin/
	sudo install -g 0 -o 0 -m 0744 project-manager.py /usr/local/lib/
