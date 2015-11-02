source := project_manager.py
completion := project_bash_completion.sh

all: project project.1.gz

project: wrapper.c
	gcc $< -o $@

project.1.gz: project.1.md
	pandoc -s -t man $< > project.1
	gzip -f project.1

install: project $(source) project.1.gz $(completion)
	install -g 0 -o 0 -m 0644 project.1.gz /usr/local/share/man/man1/
	install -g 0 -o 0 -m 4755 project /usr/local/bin/
	install -g 0 -o 0 -m 0744 $(source) /usr/local/lib/
	[ -d /usr/local/share/bash-completion ] && install -g 0 -o 0 -m 0644 $(completion) /usr/local/share/bash-completion/

test: $(source)
	nosetests

diff: $(source)
	$@ $^ /usr/local/lib/$^

tags: $(source)
	ctags $^

clean:
	rm -rf project.1.gz project *.pyc tags

.PHONY: all install test diff clean
