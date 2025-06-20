import { Link, useParams } from 'react-router-dom';
import { useAPIQuery } from 'react-router-fastapi';

interface Post {
  id: number;
  title: string;
  content: string;
  author_id: number;
  published: boolean;
  created_at: string;
  updated_at: string;
}

export const PostsPage: React.FC = () => {
  const { id: postId } = useParams<{ id: string }>();

  // If we have a postId, show post detail, otherwise show post list
  if (postId) {
    return <PostDetail postId={postId} />;
  }

  return <PostList />;
};

const PostList: React.FC = () => {
  const { 
    data: posts, 
    isLoading, 
    error 
  } = useAPIQuery<Post[]>(
    ['posts'],
    '/api/v1/posts'
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Posts Management</h1>
            <p className="text-gray-600">Create, edit and manage blog posts</p>
          </div>
          <Link
            to="/"
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            ← Home
          </Link>
        </div>

        {/* Posts Grid */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">All Posts</h2>
            {posts && (
              <p className="text-gray-600 text-sm">
                Showing {posts.length} posts
              </p>
            )}
          </div>

          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
              <span className="ml-3 text-gray-600">Loading posts...</span>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <p className="text-red-800 font-medium">Failed to load posts</p>
              <p className="text-red-600 text-sm mt-1">{error instanceof Error ? error.message : 'Unknown error'}</p>
            </div>
          )}

          {posts && posts.length > 0 && (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {posts.map((post: Post) => (
                <PostCard key={post.id} post={post} />
              ))}
            </div>
          )}

          {posts && posts.length === 0 && (
            <div className="p-12 text-center">
              <span className="text-6xl mb-4 block">📝</span>
              <p className="text-gray-500 text-lg mb-2">No posts found</p>
              <p className="text-gray-400 text-sm">Create your first post to get started</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

interface PostCardProps {
  post: Post;
}

const PostCard: React.FC<PostCardProps> = ({ post }) => {
  return (
    <div className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
          {post.title}
        </h3>
        <span
          className={`px-2 py-1 text-xs font-medium rounded-full ${
            post.published
              ? 'bg-green-100 text-green-800'
              : 'bg-yellow-100 text-yellow-800'
          }`}
        >
          {post.published ? 'Published' : 'Draft'}
        </span>
      </div>
      
      <p className="text-gray-600 text-sm mb-4 line-clamp-3">
        {post.content.substring(0, 150)}...
      </p>
      
      <div className="flex items-center justify-between text-xs text-gray-500 mb-4">
        <span>Created: {new Date(post.created_at).toLocaleDateString()}</span>
        <span>Updated: {new Date(post.updated_at).toLocaleDateString()}</span>
      </div>
      
      <Link
        to={`/posts/${post.id}`}
        className="inline-flex items-center text-blue-600 hover:text-blue-800 font-medium text-sm"
      >
        Read More →
      </Link>
    </div>
  );
};

interface PostDetailProps {
  postId: string;
}

const PostDetail: React.FC<PostDetailProps> = ({ postId }) => {
  const { data: post, isLoading, error } = useAPIQuery<Post>(
    ['post', postId],
    `/api/v1/posts/${postId}`
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Post Details</h1>
            <p className="text-gray-600">View and manage post content</p>
          </div>
          <div className="flex gap-3">
            <Link
              to="/posts"
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              ← Back to Posts
            </Link>
            <Link
              to="/"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Home
            </Link>
          </div>
        </div>

        {isLoading && (
          <div className="bg-white rounded-lg shadow-lg p-12">
            <div className="flex items-center justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
              <span className="ml-3 text-gray-600">Loading post...</span>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800 font-medium">Failed to load post</p>
              <p className="text-red-600 text-sm mt-1">{error instanceof Error ? error.message : 'Unknown error'}</p>
            </div>
          </div>
        )}

        {post && (
          <article className="bg-white rounded-lg shadow-lg p-8">
            {/* Post Header */}
            <header className="mb-8 pb-6 border-b border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <span
                  className={`px-3 py-1 text-sm font-medium rounded-full ${
                    post.published
                      ? 'bg-green-100 text-green-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}
                >
                  {post.published ? 'Published' : 'Draft'}
                </span>
                <div className="text-sm text-gray-500">
                  Author ID: {post.author_id}
                </div>
              </div>
              <h1 className="text-3xl font-bold text-gray-900 mb-4">
                {post.title}
              </h1>
              <div className="flex items-center gap-6 text-sm text-gray-600">
                <span>Created: {new Date(post.created_at).toLocaleString()}</span>
                <span>Updated: {new Date(post.updated_at).toLocaleString()}</span>
              </div>
            </header>

            {/* Post Content */}
            <div className="prose max-w-none">
              <div className="whitespace-pre-wrap text-gray-800 leading-relaxed">
                {post.content}
              </div>
            </div>

            {/* Post Footer */}
            <footer className="mt-8 pt-6 border-t border-gray-200">
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-500">
                  Post ID: {post.id}
                </div>
                <div className="flex gap-2">
                  <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
                    Edit Post
                  </button>
                  <button className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm">
                    Delete Post
                  </button>
                </div>
              </div>
            </footer>
          </article>
        )}
      </div>
    </div>
  );
}; 