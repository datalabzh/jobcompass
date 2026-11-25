{#-
    generate_schema_name.sql

    Description: schema of a model = its layer (staging, intermediate,
                 marts), without the profile schema as prefix.
    Rules: the test zone is a separate database (jobcompass_dev, target dev),
           so the schema names are the same in both databases. A model
           without +schema goes to the schema of the profile.
-#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
