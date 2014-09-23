var Tumblelog = {};

// AJAX
Tumblelog.Ajax = (function(url, callbackFunction) {
    this.bindFunction = function (caller, object) {
        return function() {
            return caller.apply(object, [object]);
        };
    };

    this.stateChange = function (object) {
        if (this.request.readyState==4) {
            this.callbackFunction(this.request.responseText);
        }
    };

    this.getRequest = function() {
        if (window.ActiveXObject)
            return new ActiveXObject('Microsoft.XMLHTTP');
        else if (window.XMLHttpRequest)
            return new XMLHttpRequest();
        return false;
    };

    this.postBody = (arguments[2] || "");
    this.callbackFunction=callbackFunction;
    this.url=url;
    this.request = this.getRequest();

    if(this.request) {
        var req = this.request;
        req.onreadystatechange = this.bindFunction(this.stateChange, this);

        if (this.postBody!=="") {
            req.open("POST", url, true);
            req.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            req.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
            req.setRequestHeader('Connection', 'close');
        } else {
            req.open("GET", url, true);
        }

        req.send(this.postBody);
    }
});

// Infinite Scroll
Tumblelog.Infinite = (function() {

    var _$window          = $(window);
    var _$posts           = $('#posts');
    var _trigger_post     = null;

    var _current_page     = CURRENT_PAGE;
    var _total_pages      = TOTAL_PAGES;
    var _url              = document.location.href;
    var _infinite_timeout = null;
    var _is_loading       = false;
    var _posts_loaded     = false;

    var _Ajax = Tumblelog.Ajax;

    function init(scrollHandler) {
        if (scrollHandler == true) {
            set_trigger();
            enable_scroll();
        }
        else {
            newPostListener();
        }
    }

    function set_trigger () {
        var $all_posts = _$posts.find('article.post');

        if (!_posts_loaded) {
            _posts_loaded = $all_posts.length;
        }

        if (_posts_loaded >= 4) {
            _trigger_post = _$posts.find('article.post:eq(' + ($all_posts.length - 4) + ')').get(0);
        } else if (_posts_loaded >= 3) {
            _trigger_post = _$posts.find('article.post:eq(' + ($all_posts.length - 3) + ')').get(0);
        } else {
            _trigger_post = _$posts.find('article.post:last').get(0);
        }

    };

    function in_viewport (el) {
        if (el == null) return;
        var top = el.offsetTop;
        var height = el.offsetHeight;

        while (el.offsetParent) {
            el = el.offsetParent;
            top += el.offsetTop;
        }

        return (top < (window.pageYOffset + window.innerHeight));
    };

    function enable_scroll() {
        $('footer .pagination').hide();
        _$window.scroll(function(){
            clearTimeout(_infinite_timeout);
            infinite_timeout = setTimeout(infinite_scroll, 100);
        });
    }

    function disable_scroll() {
        clearTimeout(_infinite_timeout);
        $(window).unbind('scroll');
    }

    function infinite_scroll() {
        if (_is_loading) return;

        if (in_viewport(_trigger_post)) {
            load_more_posts(); // w00t
        }
    };

    function load_more_posts() {
        if (_is_loading) return;
        _is_loading = true;

        // Build URL
        if (_url.charAt(_url.length - 1) != '/') _url += '/';
        if (_current_page === 1) _url += 'page/1';
        _current_page++;
        _url = _url.replace('page/' + (_current_page - 1), 'page/' + _current_page);

        console.log('load_more_posts', _url, _current_page);

        // Fetch
        _Ajax(_url, function(data) {
            var new_posts_html = data.split('<!-- START' + ' POSTS -->')[1].split('<!-- END' + ' POSTS -->')[0];
            var $new_posts = $('#posts', data);
            var new_post_div = '.page' + _current_page;

            // Insert posts and update counters
           $('#posts').append('<div class="page' + _current_page + '">' + new_posts_html + '</div>');
           sizeVideoContainers(new_post_div);
           $(new_post_div).fitVids({ customSelector: "video"});

            _posts_loaded = $new_posts.find('article.post').length;

            if ((_posts_loaded > 0) && (_current_page < _total_pages)) {
                set_trigger();
                _is_loading = false;
            } else {
                disable_scroll();
            }
        });

        // Stats
        if (typeof window._gaq != 'undefined') {
            _gaq.push(['_trackPageview', _url]);
        }
    }

    /* Infinite refresh code */

    function newPostListener() {
        if (_is_loading) return;

        setInterval(find_new_posts, 5000);
    }

    function find_new_posts() {
        if (_is_loading) {
            return;
        }

        _is_loading = true;

        // reset the url
        var liveblog_url = document.location.href;
        
        if (liveblog_url.charAt(liveblog_url.length - 1) != '/') {
            liveblog_url += '/';
        }

        liveblog_url += 'page/1';

        _Ajax(liveblog_url, function(data) {
            var $data = data;

            // Update global state
            var new_total_pages = $(data).find('#total-pages').attr('data-total-pages');

            if (new_total_pages > _total_pages) {
                _current_page += new_total_pages - _total_pages;
                _total_pages = new_total_pages;
                console.log('New page', _current_page, _total_pages);
            }

            var $posts = $(data).find('#posts').eq(0);
            var posts = $posts.children();

            var $current_posts = $('#posts');
            var current_post_permalink = $current_posts.find('.permalink').attr('href');
            var posts_to_append = [];

            for (i = 0; i < posts.length; i++) {
                var loop_post = posts[i];
                var permalink = $(loop_post).find('.permalink').attr('href');
                
                if (permalink == current_post_permalink) {
                    break;
                }

                posts_to_append.push(posts[i]);
            }

            console.log('find_new_posts', posts_to_append);

            // Insert posts and update counters

           $('#posts').prepend(posts_to_append);
           
           // TODO: #245
           sizeVideoContainers(posts_to_append);
           $(posts_to_append).fitVids({ customSelector: "video"});

            _posts_loaded = $('#posts article.post').length;

            if ((_posts_loaded > 0) && (_current_page < _total_pages)) {
                set_trigger();
                _is_loading = false;
            } else {
                disable_scroll();
            }
        });
    }

    return {
        init: init
    };
});

$(function() {
    var InfiniteScroll = new Tumblelog.Infinite;
    InfiniteScroll.init(true);

    var liveBlog = new Tumblelog.Infinite;
    liveBlog.init(false);

});
