from datetime import datetime
from server.dao.post import Post
from server.dao.category import Category
from server.dao.tag import Tag
from server.dao.post_tag import PostTag
from server.utils.exception.exception import APIException, ServerException
from server.utils.decorators.json_required import json_required
from server.utils.decorators.commit import commit

'''
    Insert
'''
def insertCategory(category_name):
    category_query = Category.queryByCategoryName(category_name)
    return (
        category_query.id 
        if category_query is not None else Category.insert(category_name=category_name).id
    )

def insertTag(tag_name):
    tag_query = Tag.queryByTagName(tag_name)
    return tag_query if tag_query is not None else Tag.insert(tag_name=tag_name)

def insertTags(tag_names):
    return [insertTag(str(tag_name)) for tag_name in tag_names]

def insertPostTag(post_id, tag_ids):
    return [
        PostTag.insert(post_id=post_id, tag_id=tag_id)
        for tag_id in tag_ids if PostTag.queryByPostIdAndTagId(post_id, tag_id) is None
    ]

'''
    Query
'''
def queryCategory(category_id):
    if category_id is not None:
        category_query = Category.queryById(category_id)
        return {
            'id': category_query.id,
            'name': category_query.category_name 
        }
    return None

def queryTags(tag_ids):
    return [
        { k: v for k, v in Tag.queryByTagId(tag_id).to_dict().items() } 
        for tag_id in tag_ids
    ]

def queryPostTags(post_id):
    return queryTags([post_tag.tag_id for post_tag in PostTag.queryByPostId(post_id)])

def queryPosts(posts):
    return [
        {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'category': queryCategory(post.category_id),
            'tags': queryPostTags(post.id),
            'created_date': post.created_date,
            'updated_date': post.updated_date,
        } 
        for post in posts
    ]

'''
    Update
'''
def updateCategory(category_name):
    category_id = None
    category_query = Category.queryByCategoryName(category_name)
    if category_query is not None:
        category_id = Category.updateByCategoryId(category_query.id, category_name=category_name).id
    else:
        category_id = Category.insert(category_name=category_name).id
    return category_id

def updatePostTags(post_id, tag_names):
    old_post_tags = PostTag.queryByPostId(post_id)
    old_tag_ids = [ post_tag.tag_id for post_tag in old_post_tags ]
    new_tag_ids = [ 
        Tag.queryByTagName(tag_name).id 
        if Tag.queryByTagName(tag_name) is not None else insertTag(tag_name).id 
        for tag_name in tag_names 
    ]
    [ PostTag.deleteByPostIdAndTagId(post_id, old_tag_id) for old_tag_id in old_tag_ids if old_tag_id not in new_tag_ids ]
    [ PostTag.insert(post_id=post_id, tag_id=new_tag_id) for new_tag_id in new_tag_ids if new_tag_id not in old_tag_ids ]

def updatePost(post_id, **update_items):
    category_name = update_items.get('category_name')
    tag_names = update_items.get('tag_names')
    if category_name is not None:
        update_items.update({ 'category_id': updateCategory(category_name) })
    if tag_names is not None:
        updatePostTags(post_id, tag_names)
    update_items.update({ 'updated_date': datetime.now() })
    Post.updateById(post_id, **update_items)

@commit
@json_required
def postPublish(params):
    title = params.get('title')
    content = params.get('content') or ''
    category_name = params.get('category_name')
    tag_names = params.get('tag_names')
    created_date = datetime.now()
    updated_date = None

    post_id = None
    category_id = None
    tag_ids = []

    if title is None:
        raise APIException('title 不能为空', 400)
    if category_name is not None:
        category_id = insertCategory(category_name)
    if (tag_names is not None):
        if (isinstance(tag_names, list) is not True):
            raise APIException('tag_names 格式不合法', 400)
        tags = insertTags(tag_names)
        tag_ids = [ tag.id for tag in tags ]
    post_id = Post.insert(
        title=title, 
        content=content, 
        category_id=category_id,
        created_date=created_date, 
        updated_date=updated_date
    ).id
    insertPostTag(post_id, tag_ids)
    return {
        'msg': '发布成功'
    }

@commit
@json_required
def postQuery(params):
    page_num = params.get('page_num') or 1
    page_size = params.get('page_size') or 10
    if isinstance(page_num, int) is not True or isinstance(page_size, int) is not True:
        raise APIException('page_num 或 page_size 格式不合法')
    posts = Post.query(page_num, page_size)
    posts_data = queryPosts(posts.items)
    return {
        'msg': '查询成功',
        'data': {
            'page_index': posts.page,
            'page_count': posts.pages,
            'total': posts.total,
            'data': posts_data
        }
    }

@commit
@json_required
def postDelete(params):
    post_id = params.get('post_id')
    if post_id is None:
        raise APIException('post_id 不能为空', 400)
    post_query= Post.queryById(post_id)
    if post_query is None:
        return {
            'msg': 'post_id 不存在'
        }
    Post.deleteById(post_id)
    PostTag.deleteByPostId(post_id)
    if len(Post.queryByCategoryId(post_query.category_id)) < 1:
        Category.deleteById(post_query.category_id)
    return {
        'msg': '删除成功'
    }

@commit
@json_required
def postUpdate(params):
    post_id = params.get('post_id')
    category_name = params.get('category_name')
    tag_names = params.get('tag_names')
    if post_id is None:
        raise APIException('post_id 不能为空', 400)
    update_items = { k: v for k, v in params.items() if k in ['title', 'content', 'category_name', 'tag_names'] }
    updatePost(post_id, **update_items) 
    return {
        'msg': '更新成功'
    }