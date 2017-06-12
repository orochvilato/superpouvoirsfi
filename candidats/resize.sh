rm thumb_*.jpg thumb_*.png
convert *.jpg -resize 25% -set filename:f 'thumb_%t.%e' +adjoin '%[filename:f]'
convert *.png -resize 25% -set filename:f 'thumb_%t.%e' +adjoin '%[filename:f]'
