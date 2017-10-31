package: clean
		@echo "Packaging ..."
		@zip -r --exclude=tests/* build.zip .

clean:
		@echo "Cleaning up ..."
		@rm -rf $(shell cat .gitignore | grep -v \#)
		@cd multiplexer && rm -rf $(shell cat .gitignore | grep -v \#)

.PHONY: build clean
