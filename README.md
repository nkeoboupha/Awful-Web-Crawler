Just needed an easy project I could throw together while trying to learn how to navigate vim.
The scope of this web crawler is to find links to unique images with their associated alt text,
perhaps to be useful in some machine learning program.

Current features:
* Should obey robots.txt
* Might listen to HTTP 429 response in some circumstances
* Stores data using sqlite3 for fast retrieval

Not yet implemented:
* Listening to 429 response while obtaining robots.txt
* Keeping a copy of relevant robots.txt rules on device
* Appropriate comments
* Proper crawl-delay logic
* Much, much more!
