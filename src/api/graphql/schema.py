"""GraphQL Schema

Defines the complete GraphQL schema for the PAKE System,
combining queries, mutations, and subscriptions.
"""

import strawberry

from .resolvers import Mutation, Query


def get_graphql_schema():
    """Create and return the GraphQL schema."""
    return strawberry.Schema(query=Query, mutation=Mutation)
