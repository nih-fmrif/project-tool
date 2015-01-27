all: project project.1.gz

project: wrapper.c
	gcc $< -o $@

project.1.gz: project.1.md
	pandoc -s -t man $< > project.1
	gzip -f project.1

install: project project_manager.py project.1.gz
	install -g 0 -o 0 -m 0644 project.1.gz /usr/local/share/man/man1
	install -g 0 -o 0 -m 4755 project /usr/local/bin/
	install -g 0 -o 0 -m 0744 project_manager.py /usr/local/lib/
	install -g 0 -o 0 -m 0744 project_check.py /usr/local/bin

test: project_manager.py
	nosetests

diff: project_manager.py
	$@ $^ /usr/local/lib/$^

clean:
	rm -rf project.1.gz project *.pyc

.PHONY: all install test diff clean
